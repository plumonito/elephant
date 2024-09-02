import torch
import numpy as np

import sys

from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor


class Sam2Processor:
    def __init__(self) -> None:
        self.device_ = torch.device("cuda")

        # use bfloat16 for the entire notebook
        torch.autocast("cuda", dtype=torch.bfloat16).__enter__()
        # turn on tfloat32 for Ampere GPUs (https://pytorch.org/docs/stable/notes/cuda.html#tensorfloat-32-tf32-on-ampere-devices)
        if torch.cuda.get_device_properties(0).major >= 8:
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        sam2_checkpoint = "sam2_repo/checkpoints/sam2_hiera_large.pt"
        model_cfg = "sam2_hiera_l.yaml"

        sam2_model = build_sam2(model_cfg, sam2_checkpoint, device=self.device_)
        self.predictor_ = SAM2ImagePredictor(sam2_model)

    def process_click(self, image: np.ndarray, point_coords: np.ndarray) -> np.ndarray:
        self.predictor_.set_image(image)
        point_labels = np.array([1])

        masks, scores, logits = self.predictor_.predict(
            point_coords,
            point_labels,
            multimask_output=True,
        )
        sorted_ind = np.argsort(scores)[::-1]
        masks = masks[sorted_ind]
        scores = scores[sorted_ind]
        logits = logits[sorted_ind]
        return masks[0]
