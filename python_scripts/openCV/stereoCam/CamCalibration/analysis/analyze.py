"""Shared analysis for two-camera, single-track Argus trials.

Examples (paths may be relative to CamCalibration or the current directory):
  argus_env/bin/python python_scripts/openCV/stereoCam/CamCalibration/analysis/analyze.py --all
  argus_env/bin/python python_scripts/openCV/stereoCam/CamCalibration/analysis/analyze.py 2026-10-17/trial_03
  Add --fall-frames 130:139 to explicitly select the orientation/focus window.
  Without that option, the last run of >=3 consecutive stereo samples is used.

Saved Argus results are preserved and shown alongside an independent 4-pixel
least-squares reconstruction. Position ranges assume 2 px independent marking
noise, fixed calibration, and simultaneous exposures; they are conditional.
"""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/freefall-matplotlib')
from pathlib import Path
import argparse,json,hashlib
import cv2
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.stats import chi2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation,PillowWriter
from matplotlib.ticker import MaxNLocator

ROOT=Path(__file__).resolve().parent.parent
REPO=ROOT.parents[3]


def select_focus(ids, frame_range=None):
    """Choose a plotting window; this does not detect physical release/contact."""
    if frame_range:
        start,end=frame_range
        mask=(ids+1>=start)&(ids+1<=end)
        if mask.sum()<3:
            raise ValueError('The focus window needs at least three matched samples.')
        return mask
    runs=np.split(np.arange(len(ids)),np.flatnonzero(np.diff(ids)!=1)+1)
    usable=[run for run in runs if len(run)>=3]
    if not usable:
        raise ValueError('No run of three consecutive stereo samples; specify --fall-frames START:END.')
    mask=np.zeros(len(ids),dtype=bool)
    mask[usable[-1]]=True
    return mask


def analyze(config_path, sigma=2., frame_range=None, animate_output=True):
    TRIAL=config_path.parent
    OUT=TRIAL/'analysis'
    OUT.mkdir(exist_ok=True)
    label=TRIAL.name.replace('_',' ').title()
    SIGMA=sigma
    # Resolve inputs from the saved project rather than assuming another trial's profile.
    import yaml
    config={k:v for item in yaml.safe_load(config_path.read_text()) for k,v in item.items()}
    def input_path(value):
        p=Path(value)
        p=p if p.is_absolute() else TRIAL/p
        if not p.is_file():raise ValueError(f'Missing input referenced in {config_path}: {p}')
        return p.resolve()
    points_path=input_path(config['points'])
    uv_all=pd.read_csv(points_path).values
    if uv_all.shape[1]!=4 or len(config['videos'])!=2:
        raise ValueError('This analysis supports one track observed by two cameras (four XY columns).')
    ids=np.flatnonzero(np.isfinite(uv_all).all(axis=1))
    if len(ids)<3:raise ValueError('At least three matched stereo samples are needed.')
    uv=uv_all[ids].reshape(-1,2,2)
    prefix=points_path.name.removesuffix('-xypts.csv')
    xyz_path=input_path(str(points_path.with_name(prefix+'-xyzpts.csv')))
    residual_path=input_path(str(points_path.with_name(prefix+'-xyzres.csv')))
    old=pd.read_csv(xyz_path).values[ids]
    old_res=pd.read_csv(residual_path).values[ids,0]
    if not np.isfinite(old).all():raise ValueError('The saved XYZ export has missing stereo locations.')
    offsets_path=input_path(config['offsets'])
    if not np.all(pd.read_csv(offsets_path).values==0):
        raise ValueError('Nonzero camera offsets need explicit video/timing alignment before analysis.')
    profile_path=input_path(config['camera_profile'])
    dlt_path=input_path(config['dlt_coefficents'])
    profile=np.loadtxt(profile_path)
    L=np.loadtxt(dlt_path,delimiter=',').T
    if profile.shape!=(2,12) or L.shape!=(2,11):
        raise ValueError('Expected two 12-column pinhole profiles and two 11-coefficient DLT columns.')
    P=np.array([np.r_[l,1].reshape(3,4) for l in L])
    dist=profile[:,-5:]
    video_paths=[input_path(v) for v in config['videos']]
    caps=[cv2.VideoCapture(str(v)) for v in video_paths]
    if not all(c.isOpened() for c in caps):raise ValueError('Could not open both source videos.')
    fps=caps[0].get(cv2.CAP_PROP_FPS)
    if fps<=0 or not all(np.isclose(c.get(cv2.CAP_PROP_FPS),fps) and c.get(cv2.CAP_PROP_FRAME_COUNT)>=len(uv_all) for c in caps):
        raise ValueError('Video frame rates differ, are invalid, or tracked frames exceed a video.')
    timing_path=TRIAL/'frame_timing.csv'
    has_timing=timing_path.is_file()
    if has_timing:
        timing=pd.read_csv(timing_path).set_index('output_frame',verify_integrity=True)
        if not set(ids+1).issubset(timing.index):raise ValueError('Timing log is missing marked frames.')
        if not np.allclose(timing.video_time_s,(timing.index.to_numpy()-1)/fps):
            raise ValueError('Timing log disagrees with AVI frame rate.')
    else:
        timing=pd.DataFrame(index=np.arange(1,len(uv_all)+1),
                            columns=['arrival_difference_s','dofbot_repeated','dashcam_repeated'],dtype=float)
    selected=timing.loc[ids+1]
    t=ids/fps
    drop=select_focus(ids,frame_range)
    first_focus=int(ids[drop][0]+1)
    last_focus=int(ids[drop][-1]+1)
    print(f'{label}: {len(ids)} samples at {fps:g} fps; focus F{first_focus}–F{last_focus}',flush=True)

    def project(x):
        q=P@np.r_[x,1.]
        ideal=q[:,:2]/q[:,2:]
        a,b=((ideal-profile[:,4:6])/profile[:,1:2]).T
        r=a*a+b*b
        k1,k2,p1,p2,k3=dist.T
        radial=1+k1*r+k2*r*r+k3*r**3
        normalized=np.column_stack((a*radial+2*p1*a*b+p2*(r+2*a*a),b*radial+p1*(r+2*b*b)+2*p2*a*b))
        return normalized*profile[:,1:2]+profile[:,4:6]

    fits=[least_squares(lambda x:(project(x)-row).ravel(),initial,xtol=1e-12,ftol=1e-12,gtol=1e-10) for row,initial in zip(uv,old)]
    assert all(f.success for f in fits)
    xyz=np.array([f.x for f in fits])
    cov=np.array([SIGMA**2*np.linalg.inv(f.jac.T@f.jac) for f in fits])
    assert np.isfinite(xyz).all() and np.all(np.linalg.eigvalsh(cov)>0)
    half=1.96*np.sqrt(np.diagonal(cov,axis1=1,axis2=2))
    predicted=np.array([project(x) for x in xyz])
    radial=np.linalg.norm(predicted-uv,axis=2)
    rms=np.sqrt(np.mean((predicted-uv)**2,axis=(1,2)))
    suspect=rms>3 # Display diagnostic, not a statistical confidence classification.
    delta=np.linalg.norm(xyz-old,axis=1)*1000
    centers=np.array([-np.linalg.solve(p[:,:3],p[:,3]) for p in P])
    # Validate the forward model and solver on exact synthetic observations.
    for target in xyz[::5]:
        test=least_squares(lambda x:(project(x)-project(target)).ravel(),target+[.001,.002,.003],gtol=1e-10)
        assert np.linalg.norm(test.x-target)<1e-7

    # One rigid rotation for points, cameras and covariance: retain real lateral motion.
    # Estimate down from the track, excluding the high-residual samples. This is a
    # presentation convention inferred from this fall, not an independent gravity measurement.
    calibration_xyz=xyz.copy()
    calibration_old=old.copy()
    calibration_centers=centers.copy()
    reliable=np.flatnonzero(drop & ~suspect)
    assert len(reliable)>=3, 'Too few reliable samples to infer the fall direction.'
    origin=xyz[reliable[:3]].mean(axis=0)
    _,_,axes=np.linalg.svd(xyz[reliable]-xyz[reliable].mean(axis=0),full_matrices=False)
    down=axes[0]
    if np.dot(down,xyz[reliable[-1]]-xyz[reliable[0]])<0:
        down=-down
    z_up=-down
    step=1e-5
    image_right=np.array([(project(origin+np.eye(3)[j]*step)[0,0]-
                           project(origin-np.eye(3)[j]*step)[0,0])/(2*step) for j in range(3)])
    x_right=image_right-z_up*np.dot(image_right,z_up)
    x_right/=np.linalg.norm(x_right)
    y_depth=np.cross(z_up,x_right)
    rotation=np.stack([x_right,y_depth,z_up])
    assert np.allclose(rotation@rotation.T,np.eye(3),atol=1e-10)
    assert np.isclose(np.linalg.det(rotation),1.)
    xyz=(xyz-origin)@rotation.T
    old=(old-origin)@rotation.T
    centers=(centers-origin)@rotation.T
    cov=np.array([rotation@c@rotation.T for c in cov])
    half=1.96*np.sqrt(np.diagonal(cov,axis1=1,axis2=2))
    assert xyz[reliable[-1],2]<xyz[reliable[0],2]
    assert np.allclose(xyz@rotation+origin,calibration_xyz)
    assert np.allclose(np.linalg.norm(np.diff(xyz,axis=0),axis=1),
                       np.linalg.norm(np.diff(calibration_xyz,axis=0),axis=1))
    view=centers[0]-xyz[drop].mean(axis=0)
    camera_azimuth=float(np.degrees(np.arctan2(view[1],view[0])))
    camera_elevation=float(np.degrees(np.arctan2(view[2],np.linalg.norm(view[:2]))))
    # Orthographic isometric view: equal foreshortening of the three unit axes.
    azimuth=-45.
    elevation=float(np.degrees(np.arctan(1/np.sqrt(2))))
    orientation={'coordinate_system':'video_aligned_fall_frame',
                 'formula':'display_xyz = rotation @ (calibration_xyz - origin)',
                 'rotation':rotation.tolist(),'origin_calibration_m':origin.tolist(),
                 'direction_fit_frames':(ids[reliable]+1).tolist(),
                 'down_direction_calibration':down.tolist(),
                 'view_camera':'orthographic isometric', 'projection':'orthographic',
                 'dashcam_azimuth_deg':camera_azimuth,
                 'dashcam_elevation_deg':camera_elevation,
                 'view_elevation_deg':elevation,'view_azimuth_deg':azimuth,
                 'axes':{'x':'Dashcam image-right projected perpendicular to inferred vertical',
                         'y':'Depth, completing a right-handed frame','z':'Up, opposite observed fall direction'},
                 'note':'Orientation inferred from this track; not surveyed gravity or floor. Rotation uncertainty is not included.'}
    (OUT/'orientation.json').write_text(json.dumps(orientation,indent=2)+'\n')

    rows=[]
    for i,idx in enumerate(ids):
        row={'frame':int(idx+1),'nominal_time_s':t[i],'phase':'selected_focus_window' if drop[i] else 'other_marked_samples',
             'raw_pixel_coordinate_rms_px':rms[i],'argus_exported_residual_px':old_res[i],
             'residual_above_3px':bool(suspect[i]),'difference_from_argus_mm':delta[i],
             'arrival_difference_ms':selected.iloc[i].arrival_difference_s*1000,
             'dofbot_repeated':bool(selected.iloc[i].dofbot_repeated) if has_timing else None,
             'dashcam_repeated':bool(selected.iloc[i].dashcam_repeated) if has_timing else None}
        for j,a in enumerate('xyz'):
            row[a+'_m']=xyz[i,j];row['argus_'+a+'_m']=old[i,j]
            row['calibration_'+a+'_m']=calibration_xyz[i,j]
            row['argus_calibration_'+a+'_m']=calibration_old[i,j]
            row[a+'_95_lower_m']=xyz[i,j]-half[i,j];row[a+'_95_upper_m']=xyz[i,j]+half[i,j]
            row[a+'_95_halfwidth_mm']=half[i,j]*1000
        rows.append(row)
    pd.DataFrame(rows).to_csv(OUT/'locations_and_uncertainty.csv',index=False)
    camera_table=pd.DataFrame(centers,index=['Dashcam','Dofbot'],columns=['x_m','y_m','z_m'])
    for j,a in enumerate('xyz'):camera_table['calibration_'+a+'_m']=calibration_centers[:,j]
    camera_table.to_csv(OUT/'camera_locations.csv',index_label='camera')

    def save(fig,name):
        fig.savefig(OUT/(name+'.png'),dpi=170,bbox_inches='tight')
        fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight');plt.close(fig)

    def setup(ax):
        ax.set(xlabel='Video-right X (m)',ylabel='Depth Y (m)',zlabel='Up Z (m)')
        for axis in [ax.xaxis,ax.yaxis,ax.zaxis]:axis.set_major_locator(MaxNLocator(4))
        ax.view_init(elev=elevation,azim=azimuth)
        ax.set_proj_type('ortho')
        ax.zaxis.labelpad=2

    def equal_scale(ax):
        limits=np.array([ax.get_xlim(),ax.get_ylim(),ax.get_zlim()])
        spans=np.ptp(limits,axis=1)
        # Include empty surrounding space so a nearly vertical track does not
        # collapse the 3D axes into an unreadable sliver. Unit scales remain equal.
        spans=np.maximum(spans,spans.max()*.65)
        middle=limits.mean(axis=1)
        ax.set(xlim=middle[0]+np.array([-.5,.5])*spans[0],
               ylim=middle[1]+np.array([-.5,.5])*spans[1],
               zlim=middle[2]+np.array([-.5,.5])*spans[2])
        ax.set_box_aspect(spans)

    def ellipsoid(ax,i):
        w,v=np.linalg.eigh(cov[i]);u,s=np.meshgrid(np.linspace(0,2*np.pi,18),np.linspace(0,np.pi,10))
        sphere=np.array([np.cos(u)*np.sin(s),np.sin(u)*np.sin(s),np.cos(s)])
        e=(v@(np.sqrt(w*chi2.ppf(.95,3))[:,None]*sphere.reshape(3,-1))).reshape(sphere.shape)+xyz[i,:,None,None]
        ax.plot_surface(*e,color='crimson' if suspect[i] else '#007b91',alpha=.16,linewidth=0)

    fig=plt.figure(figsize=(15,7));left=fig.add_subplot(121,projection='3d');right=fig.add_subplot(122,projection='3d')
    for ax in [left,right]:setup(ax)
    if (~drop).any():
        other=np.flatnonzero(~drop)
        gap_limit=max(1,float(np.median(np.diff(ids)))*3)
        for n,run in enumerate(np.split(other,np.flatnonzero(np.diff(ids[other])>gap_limit)+1)):
            left.plot(*xyz[run].T,'o--',color='#b78000',ms=4,label='Other marked samples' if n==0 else None)
    left.plot(*xyz[drop].T,'o--',color='#007b91',ms=4,label='Release/fall window')
    left.scatter(*centers.T,marker='^',s=70,color='black')
    for center,name in zip(centers,['Dashcam','Dofbot']):left.text(*center,' '+name)
    left.set_title(f'All {len(ids)} samples and camera locations');left.legend(fontsize=8)
    right.plot(*xyz[drop].T,'o--',color='#007b91',label='Independent reconstruction')
    right.scatter(*old[drop].T,color='gray',s=12,label='Argus XYZ (same rotation)')
    for i in np.flatnonzero(drop):
        ellipsoid(right,i)
        if suspect[i] or i%2==0:right.text(*xyz[i],f' F{ids[i]+1}',fontsize=8)
    right.set_title('Release/fall detail: joint 95% position regions\nRed = raw coordinate RMS above 3 px')
    right.legend(fontsize=8)
    fig.suptitle(f'{label} | {fps:g} fps | calibrated scale (m)',fontsize=15)
    for ax in [left,right]:equal_scale(ax)
    fig.text(.5,.02,f'Isometric view; fall points toward −Z. Vertical inferred from track. 95% regions assume {SIGMA:g} px noise and fixed calibration, timing and orientation.',ha='center',fontsize=9)
    fig.subplots_adjust(top=.86,bottom=.12,wspace=.12);save(fig,'reconstruction_3d')

    fig,axes=plt.subplots(2,3,figsize=(15,8))
    for j in range(3):
        for ax,mask,title in [(axes[0,j],np.ones(len(ids),dtype=bool),'Full marked track'),(axes[1,j],drop,'Release/fall window')]:
            origin=t[drop][0] if title.startswith('Release') else 0
            ax.errorbar(t[mask]-origin,xyz[mask,j],yerr=half[mask,j],fmt='o--',ms=4,capsize=3,color='#007b91',label='Independent XYZ, marginal 95%')
            ax.plot(t[mask]-origin,old[mask,j],'.',color='gray',label='Saved Argus XYZ')
            bad=mask&suspect;ax.scatter(t[bad]-origin,xyz[bad,j],marker='x',color='crimson',s=45,zorder=5)
            ax.set(title=title,xlabel='Nominal time (s)' if origin==0 else f'Time from frame {first_focus} (s)',ylabel=f'{["Video-right X","Depth Y","Up Z"][j]} (m)');ax.grid(alpha=.25)
    axes[0,0].legend(fontsize=8);fig.suptitle(f'{label}: measured positions and conditional 95% ranges');fig.tight_layout();save(fig,'locations_over_time')

    fig,axes=plt.subplots(1,3,figsize=(15,5))
    for ax,(j,k) in zip(axes,[(0,1),(0,2),(1,2)]):
        ax.errorbar(xyz[drop,j],xyz[drop,k],xerr=half[drop,j],yerr=half[drop,k],fmt='o--',capsize=3,color='#007b91')
        for i in np.flatnonzero(drop):
            if suspect[i] or i%2==0:ax.annotate(f'F{ids[i]+1}',(xyz[i,j],xyz[i,k]),xytext=(4,5),textcoords='offset points',fontsize=8,color='crimson' if suspect[i] else 'black')
        ax.set(xlabel=f'{"XYZ"[j]} (m)',ylabel=f'{"XYZ"[k]} (m)');ax.grid(alpha=.25)
    fig.suptitle('Release/fall projections | conditional marginal 95% ranges | red labels flag large residuals');fig.tight_layout();save(fig,'position_projections')

    fig,ax=plt.subplots(figsize=(6,8))
    ax.errorbar(xyz[drop,0],xyz[drop,2],xerr=half[drop,0],yerr=half[drop,2],fmt='o--',
                color='#007b91',capsize=3,label='Measured locations, marginal 95%')
    for i in np.flatnonzero(drop):
        ax.annotate(f'F{ids[i]+1}',(xyz[i,0],xyz[i,2]),xytext=(8,0),textcoords='offset points',
                    fontsize=8,color='crimson' if suspect[i] else 'black')
    ax.set(xlabel='Video-right X (m)',ylabel='Up Z (m)',title=f'{label}: video-aligned fall\nDownward motion is −Z')
    ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.25);ax.legend(fontsize=8)
    fig.text(.5,.015,'Vertical inferred from track; zero is the initial position, not the floor.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.035,1,1));save(fig,'video_aligned_view')

    fig,axes=plt.subplots(2,1,figsize=(12,7))
    axes[0].plot(ids+1,radial[:,0],'o-',label='Dashcam radial residual')
    axes[0].plot(ids+1,radial[:,1],'s-',label='Dofbot radial residual')
    axes[0].plot(ids+1,old_res,'x--',label='Argus exported residual (different metric)')
    axes[0].set(ylabel='Reprojection discrepancy (px)',xlabel='Output frame');axes[0].legend();axes[0].grid(alpha=.25)
    if has_timing:
        axes[1].plot(timing.index,timing.arrival_difference_s*1000,color='#007b91',lw=.8,label='Dofbot minus Dashcam host arrival')
        axes[1].scatter(ids+1,selected.arrival_difference_s*1000,s=15,color='#c55200',label='Marked frames')
        axes[1].legend()
    else:
        axes[1].text(.5,.5,'No host timing log available for this recording',ha='center',transform=axes[1].transAxes)
    axes[1].set(xlabel='Output frame',ylabel='Host arrival difference (ms)');axes[1].grid(alpha=.25)
    fig.suptitle('Measurement diagnostics | host arrival time is not exposure synchronization');fig.tight_layout();save(fig,'quality_and_timing')

    def read(c,frame):
        caps[c].set(cv2.CAP_PROP_POS_FRAMES,int(frame));ok,img=caps[c].read();assert ok
        return cv2.cvtColor(img,cv2.COLOR_BGR2RGB)

    sample=np.linspace(0,len(ids)-1,min(6,len(ids)),dtype=int).tolist()
    fig,axes=plt.subplots(2,len(sample),figsize=(18,7))
    for c in range(2):
        for j,i in enumerate(sample):
            ax=axes[c,j];img=read(c,ids[i]);ax.imshow(img)
            ax.plot(uv[i,c,0],img.shape[0]-uv[i,c,1],'+',color='lime',ms=14,mew=2)
            ax.plot(predicted[i,c,0],img.shape[0]-predicted[i,c,1],'o',mfc='none',mec='magenta',ms=10)
            ax.set_title(f'{["Dashcam","Dofbot"][c]} F{ids[i]+1}\nresidual {radial[i,c]:.1f} px',fontsize=10);ax.axis('off')
    fig.suptitle('Observed pixels (green) and independently reprojected 3D points (magenta)\nArgus Y flipped for video display only');fig.tight_layout(rect=(0,0,1,.91));save(fig,'camera_overlay')

    # Slow playback of measured focus frames, with no invented samples.
    schedule=np.flatnonzero(drop)
    fig=plt.figure(figsize=(14,5));axs=[fig.add_subplot(131),fig.add_subplot(132),fig.add_subplot(133,projection='3d')]
    def animate(n):
        i=schedule[n]
        for c,ax in enumerate(axs[:2]):
            ax.clear();img=read(c,ids[i]);ax.imshow(img);ax.plot(uv[i,c,0],img.shape[0]-uv[i,c,1],'+',color='lime',ms=15,mew=2);ax.axis('off');ax.set_title(['Dashcam','Dofbot'][c])
        ax=axs[2];ax.clear();setup(ax)
        sofar=schedule[:n+1];ax.plot(*xyz[sofar].T,'o--',color='#007b91');ellipsoid(ax,i);ax.text(*xyz[i],f' F{ids[i]+1}')
        low=xyz[drop].min(0)-.04;high=xyz[drop].max(0)+.04
        ax.set(xlim=(low[0],high[0]),ylim=(low[1],high[1]),zlim=(low[2],high[2]))
        equal_scale(ax)
        fig.suptitle(f'{label} | frame {ids[i]+1} | {(ids[i]-ids[drop][0])/fps:.2f} s from F{first_focus} | raw coordinate RMS {rms[i]:.2f} px\nDown = −Z; isometric view; slow playback (source {fps:g} fps); conditional 95% region',fontsize=12)
    fig.subplots_adjust(top=.8,bottom=.14,wspace=.15)
    if animate_output:
        animation=FuncAnimation(fig,animate,frames=len(schedule))
        animation.save(OUT/'reconstruction.gif',writer=PillowWriter(fps=5))
    plt.close(fig)
    for c in caps:c.release()

    results={'trial':TRIAL.name,'source_config':str(config_path),'source_fps':fps,'stereo_samples':len(ids),'frames':(ids+1).tolist(),'release_fall_frames':(ids[drop]+1).tolist(),
             'focus_selection':'explicit_frame_range' if frame_range else 'last_consecutive_stereo_run',
             'animation_regenerated':animate_output,'has_host_timing':has_timing,
             'coordinate_system':'video_aligned_fall_frame','orientation_file':'orientation.json',
             'sigma_px_assumed':SIGMA,'high_residual_frames':(ids[suspect]+1).tolist(),
             'argus_exported_residual_max_px':float(old_res.max()),'max_raw_coordinate_rms_px':float(rms.max()),
             'max_reconstruction_difference_from_argus_mm':float(delta.max()),
             'halfwidth_mm_min':(half.min(0)*1000).tolist(),'halfwidth_mm_max':(half.max(0)*1000).tolist(),
             'recording_repeats':{k:int(timing[k].sum()) for k in ['dofbot_repeated','dashcam_repeated']} if has_timing else None,
             'marked_frame_repeats':{k:int(selected[k].sum()) for k in ['dofbot_repeated','dashcam_repeated']} if has_timing else None,
             'marked_arrival_difference_ms_range':(np.array([selected.arrival_difference_s.min(),selected.arrival_difference_s.max()])*1000).tolist() if has_timing else None}
    (OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    inputs=[config_path,points_path,xyz_path,residual_path,offsets_path,profile_path,dlt_path,*video_paths,Path(__file__).resolve()]
    if has_timing:inputs.append(timing_path)
    manifest=[{'path':str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs]
    (OUT/'input_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    text=[f'{label.upper()} — SHARED ANALYSIS','',
          f'{len(ids)} matched samples at {fps:g} fps; marked frames {ids[0]+1}–{ids[-1]+1}.',
          f'Focus window: F{first_focus}–F{last_focus}, {int(drop.sum())} samples, {(last_focus-first_focus)/fps:.3f} s.',
          'Focus selection: '+results['focus_selection']+'. This selects a plotting window, not physical release.',
          'All matched samples are retained. A contiguous track can include hand contact.',
          '', 'OUTPUTS:',
          'reconstruction_3d.png/pdf: full track, camera centers and focus close-up with 95% regions.',
          'locations_over_time.png/pdf: full track and focus XYZ with marginal 95% intervals.',
          'position_projections.png/pdf: focus XY, XZ, YZ with marginal 95% intervals.',
          'video_aligned_view.png/pdf: equal-scale X-Z view with fall toward negative Z.',
          'quality_and_timing.png/pdf: reprojection errors and host timing, when available.',
          'camera_overlay.png/pdf: marked pixels and independently reprojected locations.',
          'reconstruction.gif: measured focus samples alongside both source videos.',
          'locations_and_uncertainty.csv: original/calibration XYZ, rotated XYZ, intervals and flags.',
          'camera_locations.csv: camera centers in calibration and display frames.',
          'orientation.json: rigid transform, direction-fitting samples and isometric view.',
          'results.json: sample counts, quality metrics and run options.',
          'input_manifest.json: source-file and shared-script hashes.',
          '', 'ORIENTATION:',
          'The principal direction of reliable focus samples defines down (-Z). Its sign follows time.',
          'Samples with raw coordinate RMS above 3 px are excluded from this direction fit only.',
          'Zero is the mean of the first three reliable focus samples; +X follows cam1 image-right.',
          'The 3D view is orthographic isometric: azimuth -45 degrees, elevation 35.264 degrees, Z up.',
          'Points, camera centers and covariance matrices receive the same rigid rotation.',
          'Original calibration coordinates are preserved in calibration_* CSV columns.',
          'Vertical is inferred from the selected motion, not independent gravity/floor measurements.',
          'Lateral motion is retained. Different tests can use different inferred display frames;',
          'use calibration_* coordinates for comparisons in the original shared calibration frame.',
          '', 'UNCERTAINTY AND QUALITY:',
          f'Independent XYZ minimizes all four raw distorted pixel residuals; sigma={SIGMA:g} px is assumed.',
          'Covariance = sigma^2 * inverse(J.T @ J), rotated into the display coordinate system.',
          'Marginal 95% intervals use +/-1.96 SD; joint ellipsoids use chi-square(3) at 95%.',
          'These local conditional ranges exclude calibration, exposure timing, motion blur,',
          'orientation estimation and systematic model errors. They do not measure total accuracy.',
          f'Frames with raw coordinate RMS above 3 px: {(ids[suspect]+1).tolist()}.',
          'This is a diagnostic threshold, not an estimated certainty percentage. Flagged points remain plotted.',
          f'Maximum difference from saved Argus XYZ: {delta.max():.2f} mm.',
          'Original Argus exports are preserved and shown in gray after applying the same display rotation.',
          'Independent refinement uses all four equations, avoiding the installed Argus uv_to_xyz',
          'initialization that overwrites one equation in the two-camera case.',
          f'Host timing available: {has_timing}. Missing timing is unknown, never assumed synchronized.',
          f'Reused source reads in recording: {results["recording_repeats"]}.',
          f'Reused source reads at marked frames: {results["marked_frame_repeats"]}.',
          f'Marked host arrival difference range (ms): {results["marked_arrival_difference_ms_range"]}.',
          'Host receipt timestamps are not exposure timestamps; equal output indices do not prove synchronization.',
          'No gravity magnitude or physical release/impact time is inferred from the display alignment.',
          '', 'REPRODUCE:',
          f'argus_env/bin/python {Path(__file__).relative_to(REPO)} {TRIAL.relative_to(ROOT) if TRIAL.is_relative_to(ROOT) else TRIAL}',
          'Add --fall-frames START:END to select a different focus window (1-based inclusive).',
          'Use --all to run every trial with an Argus results project. Code lives only in CamCalibration/analysis/.',
          'Original inputs remain unchanged.']
    if frame_range:text[-4]+=' --fall-frames '+str(frame_range[0])+':'+str(frame_range[1])
    if sigma!=2.:text[-4]+=f' --sigma-px {sigma:g}'
    (OUT/'report.txt').write_text('\n'.join(text)+'\n')
    print(f'  Saved {OUT}',flush=True)
    return results


def resolve_target(value):
    path=Path(value).expanduser()
    if not path.exists():path=ROOT/path
    if not path.exists():raise ValueError(f'Trial or project does not exist: {value}')
    if path.is_file():
        if not path.name.endswith('-config.yaml'):raise ValueError('Expected an Argus *-config.yaml file.')
        return path.resolve()
    configs=sorted(path.glob('*-config.yaml'))
    if len(configs)!=1:raise ValueError(f'{path} has {len(configs)} projects; specify the intended *-config.yaml.')
    return configs[0].resolve()


def parse_frame_range(value):
    try:
        first,last=map(int,value.split(':'))
        if first<1 or last<first:raise ValueError
        return first,last
    except ValueError:
        raise argparse.ArgumentTypeError('Use 1-based inclusive START:END, for example 130:139.')


def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('trial',nargs='?',help='Trial folder or Argus config, relative to CamCalibration or the current directory.')
    parser.add_argument('--all',action='store_true',help='Analyze all date/trial_* folders with an Argus project.')
    parser.add_argument('--fall-frames',type=parse_frame_range,help='Override the plotting/orientation focus window (single test only).')
    parser.add_argument('--sigma-px',type=float,default=2.,help='Assumed 1-sigma marking noise per pixel coordinate (default: 2).')
    parser.add_argument('--no-animation',action='store_true',help='Regenerate static outputs only; existing GIFs remain untouched.')
    args=parser.parse_args()
    if args.all==bool(args.trial):parser.error('Specify either a trial/config path or --all.')
    if args.all and args.fall_frames:parser.error('--fall-frames applies to a single test; omit --all.')
    if not np.isfinite(args.sigma_px) or args.sigma_px<=0:parser.error('--sigma-px must be finite and positive.')
    if args.all:
        folders=sorted(p for p in ROOT.glob('*/trial_*') if p.is_dir() and list(p.glob('*-config.yaml')))
        if not folders:parser.error('No trial result projects found.')
        targets=[resolve_target(p) for p in folders]
    else:targets=[resolve_target(args.trial)]
    failures=[]
    for config in targets:
        try:
            analyze(config,args.sigma_px,args.fall_frames,not args.no_animation)
        except (ValueError,AssertionError,OSError,KeyError,np.linalg.LinAlgError) as error:
            failures.append(str(config))
            print(f'ERROR {config}: {error}',flush=True)
        finally:
            plt.close('all')
    if failures:raise SystemExit(f'Failed analyses: {len(failures)}; see errors above.')
    print(f'Completed {len(targets)} test(s) using the shared analysis script.',flush=True)


if __name__=='__main__':main()
