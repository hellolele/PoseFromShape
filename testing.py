import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import random
import os, sys
import time
import matplotlib
matplotlib.use('agg')  # use matplotlib without GUI support

sys.path.append('./auxiliary/')
from auxiliary.model import PoseEstimator, BaselineEstimator
from auxiliary.dataset import Pix3d, Pascal3D, Linemod
from auxiliary.utils import *
from evaluation import test_category

# =================PARAMETERS=============================== #
parser = argparse.ArgumentParser()
parser.add_argument('--batch_size', type=int, default=16, help='input batch size')
parser.add_argument('--workers', type=int, help='number of data loading workers', default=2)

parser.add_argument('--shape', type=str, default=None, help='shape representation')
parser.add_argument('--model', type=str, default=None, help='optional reload model path')
parser.add_argument('--img_feature_dim', type=int, default=1024, help='feature dimension for images')
parser.add_argument('--shape_feature_dim', type=int, default=256, help='feature dimension for shapes')
parser.add_argument('--azi_classes', type=int, default=24, help='number of class for azimuth')
parser.add_argument('--ele_classes', type=int, default=12, help='number of class for elevation')
parser.add_argument('--inp_classes', type=int, default=24, help='number of class for inplane rotation')

parser.add_argument('--dataset', type=str, default=None, help='testing dataset')
parser.add_argument('--novel', action='store_true', help='whether to test on novel cats')
parser.add_argument('--keypoint', action='store_true', help='whether to use only training samples with anchors')
parser.add_argument('--num_render', type=int, default=12, help='number of render images used in each sample')
parser.add_argument('--tour', type=int, default=2, help='elevation tour for randomized references')
parser.add_argument('--random_model', action='store_true', help='whether use random model in testing')

opt = parser.parse_args()
print(opt)
# ========================================================== #


# ================CREATE NETWORK============================ #
if opt.shape is None:
    model = BaselineEstimator(img_feature_dim=opt.img_feature_dim
                              azi_classes=opt.azi_classes, ele_classes=opt.ele_classes, inp_classes=opt.inp_classes)
else:
    model = PoseEstimator(shape=opt.shape, shape_feature_dim=opt.shape_feature_dim, img_feature_dim=opt.img_feature_dim,
                          azi_classes=opt.azi_classes, ele_classes=opt.ele_classes, inp_classes=opt.inp_classes,
                          render_number=opt.num_render)
model.cuda()
if not os.path.isfile(opt.model):
    raise ValueError('Non existing file: {0}'.format(opt.model))
else:
    load_checkpoint(model, opt.model)
bin_size = 360. / opt.azi_classes
# ========================================================== #


# =============DEFINE stuff for logs ======================= #
# write basic information into the log file
result_path = os.path.split(opt.model)[0]
predictions_path = os.path.join(result_path, 'predictions')
if not os.path.isdir(predictions_path):
    os.mkdir(predictions_path)
logname = os.path.join(result_path, 'testing_log.txt')
f = open(logname, mode='w')
f.write('\n')
f.close()
# ========================================================== #


# ================TESTING LOOP============================== #
Accs = {}
Meds = {}

root_dir = os.path.join('data', opt.dataset)
annotation_file = '{}.txt'.format(opt.dataset)
if opt.dataset == 'Pascal3D':
    test_cats = ['aeroplane', 'bicycle', 'boat', 'bottle', 'bus', 'car', 'chair', 'diningtable', 'motorbike', 'sofa',
                 'train', 'tvmonitor']
    for cat in test_cats:
        dataset_test = Pascal3D(root_dir=root_dir, annotation_file=annotation_file,
                                cat_choice=[cat], train=False, mutated=False, shape=opt.shape,
                                render_number=opt.num_render, tour=opt.tour, random_model=opt.random_model)
        Accs[cat], Meds[cat] = test_category(opt.shape, opt.batch_size, opt.dataset, dataset_test, model, bin_size, cat,
                                             predictions_path, logname)


elif opt.dataset == 'ObjectNet3D':
    test_cats = ['bed', 'bookshelf', 'calculator', 'cellphone', 'computer', 'door', 'filing_cabinet', 'guitar', 'iron',
                 'knife', 'microwave', 'pen', 'pot', 'rifle', 'shoe', 'slipper', 'stove', 'toilet', 'tub', 'wheelchair']
    for cat in test_cats:
        dataset_test = Pascal3D(root_dir=root_dir, annotation_file=annotation_file,
                                cat_choice=[cat], train=False, mutated=False, keypoint=True, shape=opt.shape,
                                render_number=opt.num_render, tour=opt.tour, random_model=opt.random_model)
        Accs[cat], Meds[cat] = test_category(opt.shape, opt.batch_size, opt.dataset, dataset_test, model, bin_size, cat,
                                             predictions_path, logname)


elif opt.dataset == 'LineMod':
    test_cats = ['1', '2', '4', '5', '6', '8', '9', '10', '11', '12', '13', '14', '15']
    for cat in test_cats:
        dataset_test = Linemod(root_dir=root_dir, annotation_file=annotation_file,
                               cat_choice=[int(cat)], shape=opt.shape,
                               render_number=opt.num_render, tour=opt.tour, render_dir=opt.render_dir)
        Accs[cat], Meds[cat] = test_category(opt.shape, opt.batch_size, opt.dataset, dataset_test, model, bin_size, cat,
                                             predictions_path, logname)


elif opt.dataset == 'Pix3D':
    test_cats = ['bed', 'bookcase', 'chair', 'desk', 'misc', 'sofa', 'table', 'tool', 'wardrobe']
    for cat in test_cats:
        # use testing samples selected from the paper: https://arxiv.org/pdf/1811.07249.pdf
        if cat in ['bed', 'chair', 'desk']:
            annotation_file = '{}_annotation.txt'.format(cat)
            
        dataset_test = Pix3d(root_dir=root_dir, annotation_file=annotation_file,
                             cat_choice=[cat], shape=opt.shape, annotation_file=annotation_file,
                             render_number=opt.num_render, tour=opt.tour, random_model=opt.random_model)
        Accs[cat], Meds[cat] = test_category(opt.shape, opt.batch_size, opt.dataset, dataset_test, model, bin_size, cat,
                                             predictions_path, logname)

else:
    sys.exit(0)
# ========================================================== #


with open(logname, 'a') as f:
    f.write('Average for all categories  >>>>  Med_Err is %.2f, and Acc_pi/6 is %.2f \n' %
            (np.array(list(Meds.values())).mean(), np.array(list(Accs.values())).mean()))
