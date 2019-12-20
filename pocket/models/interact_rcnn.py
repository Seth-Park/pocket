"""
Implementation of Interact R-CNN

Fred Zhang <frederic.zhang@anu.edu.au>

The Australian National University
Australian Centre for Robotic Vision
"""

import torch
from torch import nn
from torchvision.ops import roi_align
from torchvision.ops.boxes import box_iou

class InteractionHead(nn.Module):
    """
    Arguments:
        box_pair_pooler(nn.Module)
        pooler_output_shape(tuple): (C, H, W)
        representation_size(int): Size of the intermediate representation
        num_classes(int): Number of output classes
        fg_iou_thresh(float)
        bg_iou_thresh(float)
        num_box_pairs_per_image(int): Number of box pairs used in training for each image
        positive_fraction(float): The propotion of positive box pairs used in training
    """
    def __init__(self,
            box_pair_pooler,
            pooler_output_shape, representation_size, num_classes,
            fg_iou_thresh, num_box_pairs_per_image, positive_fraction):
        
        super().__init__()

        self.box_pair_pooler = box_pair_pooler
        self.box_pair_head = nn.Sequential(
            nn.Linear(torch.as_tensor(pooler_output_shape).prod(), representation_size),
            nn.ReLU(),
            nn.Linear(representation_size, representation_size),
            nn.ReLU()
        )
        self.box_pair_logistic = nn.Linear(representation_size, num_classes)

        self.num_classes = num_classes  

        self.fg_iou_thresh = fg_iou_thresh
        self.num_box_pairs_per_image = num_box_pairs_per_image
        self.positive_fraction = positive_fraction

    def pair_up_boxes_and_assign_to_targets(self, boxes, scores, targets=None):
        """
        boxes(list[Tensor[N, 4]])
        scores(list[Tensor[N, 80]])
        target(list[dict])
        """
        if self.training and targets:
            raise AssertionError("Targets should be passed during training")
        
        box_pairs = []
        for idx in range(len(boxes)):
            object_cls = scores[idx].argmax(1)
            h_idx = (object_cls == 0).nonzero()
            paired_idx = torch.cat([
                v.flatten()[:, None] for v in torch.meshgrid(
                    h_idx, 
                    torch.arange(len(object_cls))
                )
            ], 1)
            paired_boxes = boxes[idx][paired_idx, :].view(-1, 8)

            labels = torch.zeros(len(object_cls), self.num_classes) \
                if self.training else None
            if self._training:
                target_in_image = targets[idx]  
                fg_match = torch.nonzero(torch.min(
                    box_iou(paired_boxes[:, :4], target_in_image['boxes_h']),
                    box_iou(paired_boxes[:, 4:], target_in_image['boxes_o'])
                ) >= self.fg_iou_thresh)
                labels[
                    fg_match[:, 0], 
                    target_in_image['hoi'][fg_match[:, 1]]
                ] = 1

            box_pairs.append({'paired_idx': paired_idx, 'labels': labels})

        return box_pairs

    def forward(self, features, boxes, scores, targets=None):
        """
        Arguments:
            features(list[Tensor]): Image pyramid with each tensor corresponding to
                a feature level
            boxes(list[Tensor[N, 4]]): Bounding boxes at image scale
            scores(list[Tensor[N, 80]]): Scores of boxes for each object class
            target(list[dict]): 
        Returns:
            boxes(list[Tensor[N, 4]])
            scores(list[Tensor[N, C]])
        """
        box_pairs = self.pair_up_boxes_and_assign_to_targets(boxes, scores, targets)


class InteractRCNN(nn.Module):
    def __init__(self, backbone, rpn, roi_heads, interaction_heads, transform):
        super().__init__()
        self.backbone = backbone
        self.rpn = rpn
        self.roi_heads = roi_heads
        self.interaction_heads = interaction_heads
        self.transform = transform

    def forward(self, images, targets=None):
        """
        Arguments:
            images (list[Tensor]): images to be processed
            targets (list[Dict[Tensor]], optional): ground-truth boxes present in the image
        """
        if self.training and targets is None:
            raise ValueError("In training mode, targets should be passed")
        original_image_sizes = [img.shape[-2:] for img in images]
        images, targets = self.transform(images, targets)
        features = self.backbone(images.tensors)
        proposals, proposal_losses = self.rpn(images, features, targets)
        detections, detector_losses = self.roi_heads(features, proposals,
            images.image_sizes, targets)
        detections, interaction_loss = self.interaction_heads(features, detections,
            images.image_sizes, targets)    
        detections = self.transform.postprocess(detections,
            images.image_sizes, original_image_sizes)

        losses = {}
        losses.update(detector_losses)
        losses.update(proposal_losses)
        losses.update(interaction_loss)

        if self.training:
            return losses

        return detections
