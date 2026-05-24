import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import json
import time

from ultralytics import YOLO


class YoloNode(Node):
    def __init__(self):
        super().__init__('yolo_node')
        self.bridge = CvBridge()
        self.latest_frame = None
        self.last_inference_time = 0
        self.inference_interval = 0.5  # 每0.5秒推理一次

        # 加载 YOLOv8n 模型（首次运行自动下载，约6MB）
        self.get_logger().info('Loading YOLOv8n model...')
        self.model = YOLO('yolov8n.pt')
        self.get_logger().info('YOLOv8n model loaded ✅')

        # 订阅摄像头
        self.sub_image = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )

        # 发布检测结果（JSON 字符串）
        self.pub_detections = self.create_publisher(String, '/vision/detections', 10)

        # 定时器：每0.5秒触发一次推理
        self.timer = self.create_timer(self.inference_interval, self.run_inference)

        self.get_logger().info('yolo_node started, publishing to /vision/detections')

    def image_callback(self, msg):
        """缓存最新帧，不做推理（推理由定时器触发）"""
        try:
            self.latest_frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'Image convert error: {e}')

    def run_inference(self):
        """定时触发 YOLOv8 推理"""
        if self.latest_frame is None:
            return

        frame = self.latest_frame.copy()

        try:
            results = self.model(frame, verbose=False)
            detections = []

            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = self.model.names[cls_id]
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    area = (x2 - x1) * (y2 - y1)

                    detections.append({
                        'class': cls_name,
                        'confidence': round(conf, 2),
                        'bbox': [x1, y1, x2, y2],
                        'center': [cx, cy],
                        'area': area
                    })

            # 发布结果
            msg_out = String()
            msg_out.data = json.dumps(detections, ensure_ascii=False)
            self.pub_detections.publish(msg_out)

            if detections:
                names = [f"{d['class']}({d['confidence']})" for d in detections]
                self.get_logger().info(f'Detected: {", ".join(names)}')

        except Exception as e:
            self.get_logger().error(f'Inference error: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = YoloNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
