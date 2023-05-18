
from PyQt5.QtCore import pyqtSignal, Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit
from PyQt5.QtGui import QMouseEvent
# 实时数据监测
class LineChartWidget(QWidget):
    data_updated = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)
        self.gramTitle = 'History Data'

        # 初始化数据
        self.data = [1, 1, 1, 1, 11, 11, 1, 1, 1, 2]
        self.plot_data()

    def plot_data(self):
        self.ax.clear()
        self.ax.plot(self.data)
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Value')
        self.ax.set_title(self.gramTitle)
        self.canvas.draw()

    def setTitle(self, title):
        self.gramTitle = title
        self.canvas.draw()

    def update_data(self, new_data):
        self.data = new_data
        self.plot_data()

    def mousePressEvent(self, event):
        # 模拟数据更新
        self.data = [10, 8, 6, 4, 2, 4, 6, 8, 10, 12]
        self.data_updated.emit(self.data)


class ClickableLineEdit(QLineEdit):
    clicked = pyqtSignal(QLineEdit)
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self)

        super().mousePressEvent(event) 