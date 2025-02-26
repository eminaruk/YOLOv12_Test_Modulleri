import sys
import threading
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
from ultralytics import YOLO

class VideoProcessingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

        # YOLO modelini yükle
        self.model = YOLO('yolov12n.pt')
        self.processing = False  # İşlem durumu bayrağı
        self.processing_thread = None  # İşlem için thread nesnesi

    def init_ui(self):
        self.setWindowTitle("Video İşleme Uygulaması")
        self.setGeometry(100, 100, 800, 600)

        # Layout oluştur
        layout = QVBoxLayout()

        # Butonlar oluştur
        self.detect_button = QPushButton("Nesne Tespiti Yap")
        self.blur_humans_button = QPushButton("İnsanları Bulanıklaştır")
        self.stop_button = QPushButton("İşlemi Durdur")  # Durdurma butonu

        # Butonları layout'a ekle
        layout.addWidget(self.detect_button)
        layout.addWidget(self.blur_humans_button)
        layout.addWidget(self.stop_button)  # Durdurma butonunu ekle

        # Görüntü göstermek için QLabel
        self.video_label = QLabel("Video Görüntüsü Burada Gösterilecek")
        self.video_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.video_label)

        # Butonlara tıklama olayları bağla
        self.detect_button.clicked.connect(lambda: self.process_video(self.object_detection))
        self.blur_humans_button.clicked.connect(lambda: self.process_video(self.blur_humans))
        self.stop_button.clicked.connect(self.stop_processing)  # Durdurma butonuna bağla

        self.setLayout(layout)

    def process_video(self, processing_function):
        # Video dosyasını seç
        file_path, _ = QFileDialog.getOpenFileName(self, "Bir video seçin", "", "Video Files (*.mp4 *.avi *.mov)")
        if not file_path:
            return

        # İşlem için bir thread başlat
        self.processing = True  # İşlem başladığında bayrağı True yap
        self.processing_thread = threading.Thread(target=processing_function, args=(file_path,))
        self.processing_thread.start()

    def update_video_display(self, frame):
        # OpenCV frame'i PyQt için QImage formatına dönüştür
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Pencere boyutlarına sığdırmak için yeniden boyutlandır
        frame_height, frame_width = frame.shape[:2]
        label_width = self.video_label.width()
        label_height = self.video_label.height()
        scaling_factor = min(label_width / frame_width, label_height / frame_height)
        new_width = int(frame_width * scaling_factor)
        new_height = int(frame_height * scaling_factor)
        resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

        height, width, channel = resized_frame.shape
        step = channel * width
        qimg = QImage(resized_frame.data, width, height, step, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        # QLabel üzerinde görüntüyü güncelle
        self.video_label.setPixmap(pixmap)

    def object_detection(self, file_path):
        # Nesne tespiti fonksiyonu
        def run():
            cap = cv2.VideoCapture(file_path)
            while cap.isOpened() and self.processing:  # İşlem bayrağını kontrol et
                ret, frame = cap.read()
                if not ret:
                    break

                # YOLO ile tahmin yap
                results = self.model(frame)

                # Tahmin sonuçlarını çizin
                annotated_frame = results[0].plot()

                # Ekranı güncelle
                self.update_video_display(annotated_frame)

                # Bekleme, işlem hızını kontrol eder
                cv2.waitKey(30)

            cap.release()

        threading.Thread(target=run).start()

    def blur_humans(self, file_path):
        # İnsanları bulanıklaştırma fonksiyonu
        def run():
            cap = cv2.VideoCapture(file_path)
            while cap.isOpened() and self.processing:  # İşlem bayrağını kontrol et
                ret, frame = cap.read()
                if not ret:
                    break

                # YOLO ile insan algılama
                results = self.model(frame)

                for box in results[0].boxes:
                    # Sadece insan sınıfı için işlem yap
                    if int(box.cls) == 0:  # İnsan sınıfının indexi genelde 0'dır (COCO dataset)
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        person = frame[y1:y2, x1:x2]

                        # Bölgeyi kare şeklinde bulanıklaştır
                        blurred_person = cv2.blur(person, (70, 70))
                        frame[y1:y2, x1:x2] = blurred_person

                # Ekranı güncelle
                self.update_video_display(frame)

                # Bekleme, işlem hızını kontrol eder
                cv2.waitKey(30)

            cap.release()

        threading.Thread(target=run).start()

    def stop_processing(self):
        # İşlemi durdurma bayrağını False yap
        self.processing = False
        print("İşlem durduruldu.")
        # Eğer thread çalışıyorsa beklemesini durdur
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoProcessingApp()
    window.show()
    sys.exit(app.exec_())
