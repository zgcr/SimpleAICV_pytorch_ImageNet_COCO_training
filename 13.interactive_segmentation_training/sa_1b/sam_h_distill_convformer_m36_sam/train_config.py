import os
import sys

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
sys.path.append(BASE_DIR)

from tools.path import interactive_segmentation_dataset_path

from simpleAICV.interactive_segmentation.distill_model import SAMLightDistillModel
from simpleAICV.interactive_segmentation.distill_losses import SAMDistillLoss
from simpleAICV.interactive_segmentation.datasets.sam_segmentation_dataset import SAMSegmentationDataset
from simpleAICV.interactive_segmentation.common import SamResize, SamRandomHorizontalFlip, SamNormalize, SAMBatchCollater, load_state_dict

import torch
import torchvision.transforms as transforms


class config:
    input_image_size = 1024
    mask_out_idxs = [0, 1, 2, 3]
    sigmoid_out = False
    binary_mask_out = False
    mask_threshold = 0.0
    freeze_teacher = True
    frozen_student_image_encoder = False
    frozen_student_prompt_encoder = False
    frozen_student_mask_decoder = False
    decoder_point_iters = 5
    get_point_num_per_iter = 1

    teacher_trained_model_path = '/root/autodl-tmp/pretrained_models/sam_official_pytorch_weights/sam_vit_h_4b8939.pth'
    student_trained_model_path = ''

    model = SAMLightDistillModel(
        teacher_type='sam_h',
        student_type='convformerm36_light_sam',
        teacher_params={
            'image_size': input_image_size,
            'use_gradient_checkpoint': False,
            'frozen_image_encoder': True,
            'frozen_prompt_encoder': True,
            'frozen_mask_decoder': True,
            'sigmoid_out': sigmoid_out,
            'binary_mask_out': binary_mask_out,
            'mask_threshold': mask_threshold,
        },
        student_params={
            'image_size': input_image_size,
            'use_gradient_checkpoint': False,
            'frozen_image_encoder': frozen_student_image_encoder,
            'frozen_prompt_encoder': frozen_student_prompt_encoder,
            'frozen_mask_decoder': frozen_student_mask_decoder,
            'sigmoid_out': sigmoid_out,
            'binary_mask_out': binary_mask_out,
            'mask_threshold': mask_threshold,
        },
        teacher_pretrained_path=teacher_trained_model_path,
        student_pretrained_path=student_trained_model_path,
        freeze_teacher=freeze_teacher)

    model.student.prompt_encoder.load_state_dict(
        model.teacher.prompt_encoder.state_dict())
    model.student.mask_decoder.load_state_dict(
        model.teacher.mask_decoder.state_dict())

    student_encoder_trained_model_path = '/root/autodl-tmp/pretrained_models/light_sam_encoder_distill_on_sa_1b/convformer_m36_sam_encoder_student-epoch40-loss0.003.pth'
    load_state_dict(student_encoder_trained_model_path,
                    model.student.image_encoder)

    use_single_prompt = True
    # points and boxes prob must be not both 0
    train_prompt_probs = {
        'prompt_point': 0.5,
        'prompt_box': 0.5,
        'prompt_mask': 0.,
    }
    assert 0.0 <= train_prompt_probs['prompt_point'] <= 1.0
    assert 0.0 <= train_prompt_probs['prompt_box'] <= 1.0
    assert 0.0 <= train_prompt_probs['prompt_mask'] <= 1.0

    train_criterion = SAMDistillLoss(
        **{
            'alpha': 0.8,
            'gamma': 2,
            'smooth': 1e-4,
            'distill_focal_loss_weight': 20,
            'distill_dice_loss_weight': 1,
            'distill_iou_predict_loss_weight': 1,
            'mask_threshold': mask_threshold,
        })

    train_dataset = SAMSegmentationDataset(
        interactive_segmentation_dataset_path,
        set_name=[
            'sa_000020',
            'sa_000021',
            'sa_000022',
            'sa_000023',
            'sa_000024',
            'sa_000025',
            'sa_000026',
            'sa_000027',
            'sa_000028',
            'sa_000029',
        ],
        set_type='train',
        per_set_image_choose_max_num={
            'sa_000020': 1000000,
            'sa_000021': 1000000,
            'sa_000022': 1000000,
            'sa_000023': 1000000,
            'sa_000024': 1000000,
            'sa_000025': 1000000,
            'sa_000026': 1000000,
            'sa_000027': 1000000,
            'sa_000028': 1000000,
            'sa_000029': 1000000,
        },
        per_image_mask_chosse_max_num=16,
        positive_points_num=9,
        negative_points_num=9,
        area_filter_ratio=0.0001,
        box_noise_wh_ratio=0.1,
        mask_noise_area_ratio=0.04,
        transform=transforms.Compose([
            SamResize(resize=input_image_size),
            SamRandomHorizontalFlip(prob=0.5),
            SamNormalize(mean=[123.675, 116.28, 103.53],
                         std=[58.395, 57.12, 57.375]),
        ]))

    train_collater = SAMBatchCollater(resize=input_image_size,
                                      positive_point_num_range=1)

    seed = 0
    # batch_size is total size
    batch_size = 32
    # num_workers is total workers
    num_workers = 16

    optimizer = (
        'AdamW',
        {
            'lr': 1e-5,
            'global_weight_decay': False,
            # if global_weight_decay = False
            # all bias, bn and other 1d params weight set to 0 weight decay
            'weight_decay': 0,
            'no_weight_decay_layer_name_list': [],
        },
    )

    scheduler = (
        'MultiStepLR',
        {
            'warm_up_epochs': 0,
            'gamma': 0.1,
            'milestones': [100],
        },
    )

    epochs = 5
    print_interval = 100
    save_interval = 1

    sync_bn = False
    use_amp = True
    use_compile = False
    compile_params = {
        # 'default': optimizes for large models, low compile-time and no extra memory usage.
        # 'reduce-overhead': optimizes to reduce the framework overhead and uses some extra memory, helps speed up small models, model update may not correct.
        # 'max-autotune': optimizes to produce the fastest model, but takes a very long time to compile and may failed.
        'mode': 'default',
    }

    clip_max_norm = 1.
