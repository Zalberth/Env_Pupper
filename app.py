import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QAction, QMainWindow
from PyQt5.QtCore import QDateTime,QObject,QTimer
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QMouseEvent,QIntValidator
import threading
import time
import requests
import json
from datetime import datetime
import random
from zee_utils import EnvDataQueue
from zee_utils import JSONtoCSV
from zee_widgets import LineChartWidget, ClickableLineEdit


# 设计一个线程后台拉取数据，每隔固定时间根据当前激活的lineEdit来刷新canvas
class SensorThread(QObject):
    data_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.url = "http://192.168.2.222:33200/sensor/getAllSensor"
        self.update_interval = 1  # 默认更新周期为1秒
        self.is_running = False
        self.timer = QTimer()
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # 使用时间戳作为文件名的一部分
        csv_filename = f"./env-data/env_data_{timestamp}.csv"
        self.json_to_csv = JSONtoCSV(csv_filename=csv_filename)

    def set_update_interval(self, interval):
        self.update_interval = interval

    def get_sensor_data(self):
        try:
            response = requests.get(self.url, timeout=5)
            if response.status_code == 200:
                json_data = response.json()
                json_sensor_data = json_data['data']['sensor']
                
                timestamp = datetime.now().timestamp()  # 获取当前时间的时间戳
                # 将时间戳转换为 datetime 对象
                dt = datetime.fromtimestamp(timestamp)
                # 将 datetime 对象格式化为字符串（精确到毫秒）
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S.%f")  # 格式化为 "年-月-日 时:分:秒.毫秒" 的格式
                # 将时间戳添加到 json_sensor_data 中
                json_sensor_data['timestamp'] = formatted_time
                self.data_updated.emit(json_sensor_data)
                self.json_to_csv.add_data(json_sensor_data)
            else:
                print("请求失败，状态码：", response.status_code)

        except requests.RequestException as e:
            print("请求发生异常:", e)

    def start_collection(self):
        self.is_running = True
        self.timer.timeout.connect(self.get_sensor_data)
        self.timer.start(self.update_interval * 1000)  # 根据设置的秒数转换为毫秒

    def stop_collection(self):
        self.is_running = False
        self.timer.stop()


class DataDisplayThread(QObject):
    lineChart = None

    def __init__(self, lineChartWgt, parent=None):
        super().__init__(parent)
        self.lineChart = lineChartWgt
        self.update_interval = 1  # 默认更新周期为1秒
        self.is_running = False
        self.timer = QTimer()
        self.datalist = []
        self.dataQueue = EnvDataQueue(10)
        
    def setList(self, myqueue, title = "HS Data"):
        self.dataQueue = myqueue
        self.lineChart.setTitle(title)
        pass

    def update_env_data_graph(self):
        self.lineChart.update_data(self.dataQueue.get_data_list())
        pass

    def start_display(self):
        self.is_running = True
        self.timer.timeout.connect(self.update_env_data_graph)
        self.timer.start(self.update_interval * 1000)  # 根据设置的秒数转换为毫秒

    def stop_display(self):
        self.is_running = False
        self.timer.stop()


class InputTextWindow(QMainWindow):
    current_time = ""
    lastLineEdit = None

    def __init__(self):
        super().__init__()

        self.init_ui()
        self.sensor_thread = SensorThread()
        self.sensor_thread.data_updated.connect(self.update_line_edits)
        self.updateLineChartThread = DataDisplayThread(self.line_chart)
        # 创建多个队列
        self.noise_queue = EnvDataQueue(10)
        self.temperature_queue = EnvDataQueue(10)
        self.humidity_queue = EnvDataQueue(10)
        self.pm25_queue = EnvDataQueue(10)
        

    def init_ui(self):
        """初始化界面"""
        # set this window to full screen mode after running on this macos
        self.setFixedSize(900, 800) 
        self.setWindowTitle("ENV-DATA-ACQUIRER")
        self.setGeometry(100, 100, 300, 150)

        # create a menubar
        self.menubar = self.menuBar()
        # create a menu
        self.tool_menu = self.menubar.addMenu("工具")
        # create a action
        self.setting_action = QAction("设置", self)
        self.exit_action = QAction("退出", self)

        self.tool_menu.addAction(self.setting_action)
        self.tool_menu.addAction(self.exit_action)

        # 连接菜单项的信号和槽函数
        self.exit_action.triggered.connect(self.close) 

        layout = QVBoxLayout()
      

        hLayout = QHBoxLayout()
        self.label = QLabel("读取频率")
        hLayout.addWidget(self.label)
        self.freqLineEdit = QLineEdit()
        self.freqLineEdit.setText("1")
        self.freqLineEdit.setValidator(QIntValidator())  # 限制只能输入整数
        hLayout.addWidget(self.freqLineEdit)
        self.submit_button = QPushButton("开始读取")
        self.submit_button.clicked.connect(self.start_collection)
        self.submit_button.setStyleSheet("background-color: red; color: white")
        hLayout.addWidget(self.submit_button)
       
        layout.addLayout(hLayout)
        
        # q: please create a grid layout whitch contains 5 rows and 8 columns
        # a:    
        #    1. create a grid layout
        #    2. create 5 rows and 8 columns
        #    3. add 5 rows and 8 columns to the grid layout
        #    4. add the grid layout to the vertical layout
        # the json data is shown as below:
        # {
        #         "deviceType": "LY-QX12",
        #         "deviceId": "MT5934453861",
        #         "timestamp": "1683544395",
        #         "sensor": {
        #                 "Noise": "35",
        #                 "Temperature": "-6",
        #                 "Humidity": "45.6",
        #                 "Wind_Speed": "24.3",
        #                 "Wind_Direction": "254",
        #                 "Rainfall": "6.5",
        #                 "Radiation": "1008",
        #                 "Illumination": "85000",
        #                 "AirPressure": "998",
        #                 "PM2.5": "32",
        #                 "PM10": "43",
        #                 "Ultraviolet_Ray": "7",
        #                 "CO": "12",
        #                 "SO2": "600",
        #                 "NO2": "700",
        #                 "O3": "800",
        #                 "TVOC": "11",
        #                 "PersonTotal", "1",
        #                 "CarTotal": "2",
        #                 "EVCarTotal": "1",
        #                 "GasCarTotal": "1"
        #         }
        # }
        # according the above json, the sensor part

        # row 1
        gridLayout = QGridLayout()
        gridLayout.setSpacing(1)   
        # q: what is setSpacing in QGridLayout?
        # a: setSpacing is a function that sets the spacing between widgets in the layout to spacing.     
        self.noiseLabel = QLabel("噪声")
        gridLayout.addWidget(self.noiseLabel, 0, 0)
        self.noiseLineEdit = ClickableLineEdit()
        self.noiseLineEdit.setReadOnly(True)
        self.noiseLineEdit.setObjectName("noise")
        self.noiseLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        self.noiseLineEdit.clicked.connect(self.on_click)
        gridLayout.addWidget(self.noiseLineEdit, 0, 1)
        self.noiseUnitLabel = QLabel("dB")
        gridLayout.addWidget(self.noiseUnitLabel, 0, 2)

        self.temperatureLabel = QLabel("温度")
        gridLayout.addWidget(self.temperatureLabel, 0, 3)
        self.temperatureLineEdit = ClickableLineEdit()
        self.temperatureLineEdit.setReadOnly(True)
        self.temperatureLineEdit.setObjectName("temperature")
        self.temperatureLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        self.temperatureLineEdit.clicked.connect(self.on_click)
        gridLayout.addWidget(self.temperatureLineEdit, 0, 4)
        self.temperatureUnitLabel = QLabel("℃")
        gridLayout.addWidget(self.temperatureUnitLabel, 0, 5)

        self.humidityLabel = QLabel("湿度")
        gridLayout.addWidget(self.humidityLabel, 0, 6)
        self.humidityLineEdit = ClickableLineEdit()
        self.humidityLineEdit.setReadOnly(True)
        self.humidityLineEdit.setObjectName("humidity")
        self.humidityLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        self.humidityLineEdit.clicked.connect(self.on_click)
        gridLayout.addWidget(self.humidityLineEdit, 0, 7)
        self.humidityUnitLabel = QLabel("%")
        gridLayout.addWidget(self.humidityUnitLabel, 0, 8)

        self.windspeedLabel = QLabel("风速")
        gridLayout.addWidget(self.windspeedLabel, 0, 9)
        self.windspeedLineEdit = ClickableLineEdit()
        self.windspeedLineEdit.setReadOnly(True)
        self.windspeedLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.windspeedLineEdit, 0, 10)
        self.windspeedUnitLabel = QLabel("m/s")
        gridLayout.addWidget(self.windspeedUnitLabel, 0, 11)

        # row 2
        self.Wind_DirectionLabel = QLabel("风向")
        gridLayout.addWidget(self.Wind_DirectionLabel, 1, 0)
        self.Wind_DirectionLineEdit = ClickableLineEdit()
        self.Wind_DirectionLineEdit.setReadOnly(True)
        self.Wind_DirectionLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.Wind_DirectionLineEdit, 1, 1)
        self.Wind_DirectionUnitLabel = QLabel("°")
        gridLayout.addWidget(self.Wind_DirectionUnitLabel, 1, 2)
        self.RainfallLabel = QLabel("降雨量")
        gridLayout.addWidget(self.RainfallLabel, 1, 3)
        self.RainfallLineEdit = ClickableLineEdit()
        self.RainfallLineEdit.setReadOnly(True)
        self.RainfallLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.RainfallLineEdit, 1, 4)
        self.RainfallUnitLabel = QLabel("mm")
        gridLayout.addWidget(self.RainfallUnitLabel, 1, 5)
        self.RadiationLabel = QLabel("辐射")
        gridLayout.addWidget(self.RadiationLabel, 1, 6)
        self.RadiationLineEdit = ClickableLineEdit()
        self.RadiationLineEdit.setReadOnly(True)
        self.RadiationLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.RadiationLineEdit, 1, 7)
        self.RadiationUnitLabel = QLabel("W/m2")
        gridLayout.addWidget(self.RadiationUnitLabel, 1, 8)
        self.IlluminationLabel = QLabel("光照")
        gridLayout.addWidget(self.IlluminationLabel, 1, 9)
        self.IlluminationLineEdit = ClickableLineEdit()
        self.IlluminationLineEdit.setReadOnly(True)
        self.IlluminationLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.IlluminationLineEdit, 1, 10)
        self.IlluminationUnitLabel = QLabel("Lux")
        gridLayout.addWidget(self.IlluminationUnitLabel, 1, 11)

        # row 3
        self.AirPressureLabel = QLabel("气压")
        gridLayout.addWidget(self.AirPressureLabel, 2, 0)
        self.AirPressureLineEdit = ClickableLineEdit()
        self.AirPressureLineEdit.setReadOnly(True)
        self.AirPressureLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.AirPressureLineEdit, 2, 1)
        self.AirPressureUnitLabel = QLabel("hPa")
        gridLayout.addWidget(self.AirPressureUnitLabel, 2, 2)
        self.PM2_5Label = QLabel("PM2.5")
        gridLayout.addWidget(self.PM2_5Label, 2, 3)
        self.PM2_5LineEdit = ClickableLineEdit()
        self.PM2_5LineEdit.setReadOnly(True)
        self.PM2_5LineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.PM2_5LineEdit, 2, 4)
        self.PM2_5UnitLabel = QLabel("μg/m3")
        gridLayout.addWidget(self.PM2_5UnitLabel, 2, 5)
        self.PM10Label = QLabel("PM10")
        gridLayout.addWidget(self.PM10Label, 2, 6)
        self.PM10LineEdit = ClickableLineEdit()
        self.PM10LineEdit.setReadOnly(True)
        self.PM10LineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.PM10LineEdit, 2, 7)
        self.PM10UnitLabel = QLabel("μg/m3")
        gridLayout.addWidget(self.PM10UnitLabel, 2, 8)
        self.Ultraviolet_RayLabel = QLabel("紫外线")
        gridLayout.addWidget(self.Ultraviolet_RayLabel, 2, 9)
        self.Ultraviolet_RayLineEdit = ClickableLineEdit()
        self.Ultraviolet_RayLineEdit.setReadOnly(True)
        self.Ultraviolet_RayLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.Ultraviolet_RayLineEdit, 2, 10)
        self.Ultraviolet_RayUnitLabel = QLabel("μg/m3")
        gridLayout.addWidget(self.Ultraviolet_RayUnitLabel, 2, 11)

        # row 4
        self.COLabel = QLabel("CO")
        gridLayout.addWidget(self.COLabel, 3, 0)
        self.COLineEdit = ClickableLineEdit()   
        self.COLineEdit.setReadOnly(True)
        self.COLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.COLineEdit, 3, 1)
        self.COUnitLabel = QLabel("μg/m3")
        gridLayout.addWidget(self.COUnitLabel, 3, 2)
        self.SO2Label = QLabel("SO2")
        gridLayout.addWidget(self.SO2Label, 3, 3)
        self.SO2LineEdit = ClickableLineEdit()
        self.SO2LineEdit.setReadOnly(True)
        self.SO2LineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.SO2LineEdit, 3, 4)
        self.SO2UnitLabel = QLabel("μg/m3")
        gridLayout.addWidget(self.SO2UnitLabel, 3, 5)
        self.NO2Label = QLabel("NO2")
        gridLayout.addWidget(self.NO2Label, 3, 6)
        self.NO2LineEdit = ClickableLineEdit()
        self.NO2LineEdit.setReadOnly(True)
        self.NO2LineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.NO2LineEdit, 3, 7)
        self.NO2UnitLabel = QLabel("μg/m3")
        gridLayout.addWidget(self.NO2UnitLabel, 3, 8)
        self.O3Label = QLabel("O3")
        gridLayout.addWidget(self.O3Label, 3, 9)
        self.O3LineEdit = ClickableLineEdit()
        self.O3LineEdit.setReadOnly(True)
        self.O3LineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.O3LineEdit, 3, 10)
        self.O3UnitLabel = QLabel("μg/m3")
        gridLayout.addWidget(self.O3UnitLabel, 3, 11)

        # row 5
        self.TVOCLabel = QLabel("TVOC")
        gridLayout.addWidget(self.TVOCLabel, 4, 0)
        self.TVOCLineEdit = ClickableLineEdit()
        self.TVOCLineEdit.setReadOnly(True)
        self.TVOCLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.TVOCLineEdit, 4, 1)
        self.TVOCUnitLabel = QLabel("μg/m3")
        gridLayout.addWidget(self.TVOCUnitLabel, 4, 2)
        self.PersonTotalLabel = QLabel("人数")
        gridLayout.addWidget(self.PersonTotalLabel, 4, 3)
        self.PersonTotalLineEdit = ClickableLineEdit()
        self.PersonTotalLineEdit.setReadOnly(True)
        self.PersonTotalLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.PersonTotalLineEdit, 4, 4)
        self.PersonTotalUnitLabel = QLabel("人")
        gridLayout.addWidget(self.PersonTotalUnitLabel, 4, 5)
        self.CarTotalLabel = QLabel("车辆数")
        gridLayout.addWidget(self.CarTotalLabel, 4, 6)
        self.CarTotalLineEdit = ClickableLineEdit()
        self.CarTotalLineEdit.setReadOnly(True)
        self.CarTotalLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.CarTotalLineEdit, 4, 7)
        self.CarTotalUnitLabel = QLabel("辆")
        gridLayout.addWidget(self.CarTotalUnitLabel, 4, 8)
        self.EVCarTotalLabel = QLabel("新能源车辆数")
        gridLayout.addWidget(self.EVCarTotalLabel, 4, 9)
        self.EVCarTotalLineEdit = ClickableLineEdit()
        self.EVCarTotalLineEdit.setReadOnly(True)
        self.EVCarTotalLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.EVCarTotalLineEdit, 4, 10)
        self.EVCarTotalUnitLabel = QLabel("辆")
        gridLayout.addWidget(self.EVCarTotalUnitLabel, 4, 11)

        # row 6
        self.GasCarTotalLabel = QLabel("燃油车辆数")
        gridLayout.addWidget(self.GasCarTotalLabel, 5, 0)
        self.GasCarTotalLineEdit = ClickableLineEdit()
        self.GasCarTotalLineEdit.setReadOnly(True)
        self.GasCarTotalLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        gridLayout.addWidget(self.GasCarTotalLineEdit, 5, 1)
        self.GasCarTotalUnitLabel = QLabel("辆")
        gridLayout.addWidget(self.GasCarTotalUnitLabel, 5, 2)

        self.line_chart = LineChartWidget()
        layout.addLayout(gridLayout)
        layout.addWidget(self.line_chart)
        # self.setLayout(layout)

        # 创建一个容器窗口，并将布局设置给容器窗口
        container = QWidget()
        container.setLayout(layout)

        # 将容器窗口设置为中央部件
        self.setCentralWidget(container)

    def display_noise_activity(self, input_obj):
        print("执行噪声逻辑")
        print(self.noise_queue.get_data_list())
        self.updateLineChartThread.setList(self.noise_queue, 'Noise Data')


    def display_temperature_activity(self, input_obj):
        print("执行温度逻辑")
        print(self.temperature_queue.get_data_list())
        self.updateLineChartThread.setList(self.temperature_queue, 'Temperature Data')

    def display_humidity_activity(self, input_obj):
        print("执行湿度逻辑")

    def display_func_select(self, string):
        logic_map = {
            "noise": self.display_noise_activity,
            "temperature": self.display_temperature_activity,
            "humidity": self.display_humidity_activity,
        }        
        logic_function = logic_map.get(string, self.display_noise_activity)
        return logic_function

    def start_collection(self):
        if self.sensor_thread.is_running:
            self.sensor_thread.stop_collection()
            self.freqLineEdit.setEnabled(True)
            self.submit_button.setText("开始读取")
            # q: set background color of submit_button to red only
            # a: use setStyleShee
            self.submit_button.setStyleSheet("background-color: red; color: white")
            self.updateLineChartThread.stop_display()
        else:
            oriText = self.freqLineEdit.text()
            if oriText.strip() != "":
                interval = int(oriText)
                if interval > 0:
                    self.sensor_thread.set_update_interval(interval)
                    self.sensor_thread.start_collection()
                    self.freqLineEdit.setEnabled(False)
                    self.submit_button.setText("停止读取")
                    self.submit_button.setStyleSheet("background-color: green; color: white")
                    self.updateLineChartThread.start_display()

    def update_line_edits(self, json_data):
        self.noiseLineEdit.setText(json_data.get("Noise"))
        self.temperatureLineEdit.setText(json_data.get("Temperature"))
        self.humidityLineEdit.setText(json_data.get("Humidity"))
        self.windspeedLineEdit.setText(json_data.get("Wind_Speed"))
        self.Wind_DirectionLineEdit.setText(json_data.get("Wind_Direction"))
        self.RainfallLineEdit.setText(json_data.get("Rainfall"))
        self.RadiationLineEdit.setText(json_data.get("Radiation"))
        self.IlluminationLineEdit.setText(json_data.get("Illumination"))
        self.AirPressureLineEdit.setText(json_data.get("AirPressure"))
        self.PM2_5LineEdit.setText(json_data.get("PM2.5"))
        self.PM10LineEdit.setText(json_data.get("PM10"))
        self.Ultraviolet_RayLineEdit.setText(json_data.get("Ultraviolet_Ray"))
        self.COLineEdit.setText(json_data.get("CO"))
        self.SO2LineEdit.setText(json_data.get("SO2"))
        self.NO2LineEdit.setText(json_data.get("NO2"))
        self.O3LineEdit.setText(json_data.get("O3"))
        self.TVOCLineEdit.setText(json_data.get("TVOC"))
        self.PersonTotalLineEdit.setText(json_data.get("People_Number"))
        self.CarTotalLineEdit.setText(json_data.get("Car_Sum"))
        self.EVCarTotalLineEdit.setText(json_data.get("Car_Number_green"))
        self.GasCarTotalLineEdit.setText(json_data.get("Car_Number_Notgreen"))

        # push data to queue
        self.noise_queue.push_data(float(json_data.get("Noise")))
        self.temperature_queue.push_data(float(json_data.get("Temperature")))
        self.humidity_queue.push_data(float(json_data.get("Humidity")))
        self.pm25_queue.push_data(json_data.get("PM2.5"))


    # 点击事件，用于切换显示的数据样式                 
    def on_click(self, line_edit):
        print("LineEdit click:", line_edit.objectName())
        self.display_func_select(line_edit.objectName())(self.line_chart)
        line_edit.setStyleSheet("background-color: #ccccd9; color: red")
        if self.lastLineEdit != None:
            self.lastLineEdit.setStyleSheet("background-color: #ccccd9; color: black")
        self.lastLineEdit = line_edit
                
def main():
    app = QApplication(sys.argv)
    window = InputTextWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
