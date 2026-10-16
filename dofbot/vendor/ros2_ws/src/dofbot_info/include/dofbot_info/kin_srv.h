#ifndef __KIN_SRV_H__
#define __KIN_SRV_H__

#include <kdl/chain.hpp>
#include <kdl/tree.hpp>
#include <kdl/segment.hpp>
#include <kdl/frames_io.hpp>
#include <kdl/chainiksolverpos_lma.hpp>
#include <kdl/chainfksolverpos_recursive.hpp>
#include <kdl_parser/kdl_parser.hpp>
#include <iostream>
#include <kdl/chain.hpp>
#include <kdl/chainfksolver.hpp>
#include <kdl/tree.hpp>
#include <kdl_parser/kdl_parser.hpp>
#include <kdl_parser/kdl_parser.hpp>

using namespace KDL;
using namespace std;

bool arm_getFK(const char *urdf_file, vector<double> &joints, vector<double> &currentPos);

bool arm_getIK(const char *urdf_file, vector<double> &targetXYZ, vector<double> &targetRPY, vector<double> &outjoints);

#endif 
