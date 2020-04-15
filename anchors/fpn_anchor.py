import torch


class FpnAnchor:
    def __init__(self, pyramid_size, depth, box_sizes, ratios):
        boxes = []

        for i in range(depth):
            step = 1.0 / pyramid_size

            for j in range(pyramid_size):
                cy = (j + 0.5) * step

                for i in range(pyramid_size):
                    cx = (i + 0.5) * step

                    for b in box_sizes:
                        for r in ratios:
                            w = step * b * r
                            h = step * b / r

                            boxes.append([cx, cy, w, h])

            pyramid_size = (pyramid_size + 1) // 2

        boxes = torch.tensor(boxes).detach()

        if torch.cuda.is_available():
            boxes = boxes.cuda()

        self.anchors = boxes

    # (x1, y1, x2, y2) -> (delta_x, delta_y, delta_w, delta_h)
    def encode(self, raw):
        has_batch = len(raw.shape) == 3

        if not has_batch:
            raw = raw.unsqueeze(0)

        anchor = self.anchors.unsqueeze(0).expand_as(raw)

        # (x1, y1, x2, y2) -> (cx, cy, w, h)
        cxcy = (raw[:, :, 2:4] + raw[:, :, 0:2]) / 2.
        wh = raw[:, :, 2:4] - raw[:, :, 0:2]

        anchor_cxcy = anchor[:, :, 0:2]
        anchor_wh = anchor[:, :, 2:4]

        # delta_x = (x - anchor_x) / anchor_width
        delta_xy = (cxcy - anchor_cxcy) / anchor_wh

        # delta_w = ln(width / anchor_width)
        delta_wh = torch.log(wh / anchor_wh)

        encoded = torch.cat((delta_xy, delta_wh), 2)
        if not has_batch:
            encoded = encoded.squeeze(0)

        return encoded / 0.1

    # (delta_x, delta_y, delta_w, delta_h) -> (x1, y1, x2, y2)
    def decode(self, encoded):
        has_batch = len(encoded.shape) == 3

        encoded *= 0.1

        if not has_batch:
            encoded = encoded.unsqueeze(0)

        anchor = self.anchors.expand_as(encoded)

        # delta_x * anchor_width + anchor_x
        xy = encoded[:, :, 0:2] * anchor[:, :, 2:4] + anchor[:, :, 0:2]

        # exp(delta_w) * anchor_width
        half_wh = torch.exp(encoded[:, :, 2:4]) * anchor[:, :, 2:4] / 2.

        raw = torch.cat((xy - half_wh, xy + half_wh), 2)
        if not has_batch:
            raw = raw.squeeze(0)

        return raw

    def get_anchor(self):
        return self.anchors
