import PyQt5
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.uic import loadUi
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt5.QtWidgets import QLCDNumber, QPushButton, QLabel, QTimeEdit 
from PyQt5.QtCore import QIODevice, QPoint
from PyQt5 import QtCore, QtWidgets 
from openpyxl import Workbook
from PyQt5.QtWidgets import QFileDialog, QDialog
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QPixmap
import pyqtgraph as pg
import numpy as np
import sys
import pandas as pd
import csv
import os
import time
from InterfazTribometroPinOnDisk import Ui_MainWindow



class TimerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QLabel("Tiempo requerido (HH:MM:SS):", self)
        self.label.setGeometry(10, 10, 200, 30)
        self.time_edit = QTimeEdit(self)
        self.time_edit.setDisplayFormat("HH:mm:ss")
        self.time_edit.setGeometry(210, 10, 80, 30)
        self.ok_button = QPushButton("Aceptar", self)
        self.ok_button.setGeometry(100, 50, 100, 30)
        self.ok_button.clicked.connect(self.accept)


class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.drag_start_position = None
        self.ui.bt_normal.hide()
        self.click_posicion = QPoint()
        self.ui.bt_minimize.clicked.connect(lambda: self.showMinimized())
        self.ui.bt_normal.clicked.connect(self.control_bt_normal)
        self.ui.bt_maximize.clicked.connect(self.control_bt_maximize)
        self.ui.bt_close.clicked.connect(lambda: self.close())

        # Eliminar barra de titulo y opacidad
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setWindowOpacity(1)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # SizeGrip
        self.gripSize = 10
        self.grip = QtWidgets.QSizeGrip(self)
        self.grip.resize(self.gripSize, self.gripSize)
        # mover ventana
        self.ui.frame_superior.mouseMoveEvent = self.mover_ventana
        # Llama a la función para mostrar el mensaje de precaución al iniciar la aplicación
        self.mostrar_mensaje_precaucion()
        ## control connect
        self.serial = QSerialPort()
        self.ui.bt_update.clicked.connect(self.read_ports)
        self.ui.bt_connect.clicked.connect(self.serial_connect)
        self.ui.bt_disconnect.clicked.connect(self.serial_disconnect)
        self.ui.bt_exportar.clicked.connect(self.exportar_datos)
        self.ui.bt_start.clicked.connect(self.start_receiving_data)
        self.ui.bt_stop.clicked.connect(self.pause_temporizador)
        self.ui.bt_reset.clicked.connect(self.reset_temporizador)
        self.ui.bt_temporizador.clicked.connect(self.show_timer_dialog)
        self.ui.bt_Reinicio_Graficas.clicked.connect(self.reset_graficas)
        # self.serial.readyRead.connect(self.read_data)

        # Inicializar el temporizador pero no comenzar a contar
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.time_required = QTime(0, 0)
        self.remaining_time = QTime(0, 0)

        # Lcd
        # Agregar un QLCDNumber para mostrar el tiempo del cronómetro
        self.lcdCronometro = self.findChild(QLCDNumber, 'lcdCronometro')
        # Crear un QTimer para el cronómetro
        self.lcdCronometro.setDigitCount(8)  # Establecer 8 dígitos para horas:minutos:segundos
        self.lcdCronometro.setSegmentStyle(QLCDNumber.Filled)
        self.lcdCronometro.display("00:00:00")  # Inicializar el valor a 00:00:00
        self.lcdCronometro = self.findChild(QLCDNumber, 'lcdCronometro')
        self.tiempo = 0  # Representa el tiempo en segundos
        self.ultimoTiempo = 99999999  # Representa el ultimo tiempo
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)

        # GRAFICA
        pg.setConfigOption('background', '#ffffff')
        pg.setConfigOption('foreground', '#143153')
        # Nombre de las Graficas
        self.plt_1 = pg.PlotWidget(title='Humedad')
        self.plt_2 = pg.PlotWidget(title='Temperatura')
        self.plt_3 = pg.PlotWidget(title='Distancia')
        self.plt_4 = pg.PlotWidget(title='Coeficiente de Friccion')

        # configurar las cuatro listas
        self.x = list(np.linspace(0, 100, 100))
        self.y1 = []
        self.y2 = []
        self.y3 = []
        self.y4 = []

        # Agregar las cuatro graficas al diseño colocar los nombre que aparecene en el Qt designer
        self.ui.graph_layout_humedad.addWidget(self.plt_1)
        self.ui.graph_layout_temperatura.addWidget(self.plt_2)
        self.ui.graph_layout_velocidad.addWidget(self.plt_3)
        self.ui.graph_layout_friccion.addWidget(self.plt_4)
        self.max_data_len = 10  # Establece la longitud máxima para mostrar en la gráfica
        self.data_history = {
            'var1': [],
            'var2': [],
            'var3': [],
            'var4': []
        }
        self.plot_start = 0  # Inicialización de la variable para controlar el inicio de la gráfica

        # Datos
        self.mi_variable1 = 0.00  # Inicializa la variable para el primer DoubleSpinBox
        self.mi_variable2 = 0.00  # Inicializa la variable para el segundo DoubleSpinBox
        # Conecta la señal valueChanged de los DoubleSpinBox a funciones para actualizar las variables
        self.ui.doubleSpinBox1.valueChanged.connect(self.actualizar_variable1)
        self.ui.doubleSpinBox2.valueChanged.connect(self.actualizar_variable2)

    def mostrar_mensaje_precaucion(self):
        mensaje = QMessageBox(self)
        mensaje.setWindowTitle("Mensaje de precaución")
        texto = """
            <html>
    <body>
        <div style="text-align:center; color:red; font-size:30px; font-weight:bold;">
            ¡Alerta!
        </div>
        <div style="text-align:center;">
            <i class="fas fa-exclamation-triangle" style="color: orange; font-size: 18px;"></i>
        </div>
        <div>
            <b>Pasos:</b>
            <ol>
                <li>Acepte las recomendaciones emergentes para el correcto funcionamiento.</li>
                <li>Verifique y asegúrese de que el Arduino esté correctamente conectado y detectado en la sección de configuración.</li>
                <li>Establezca la velocidad de baudios en 9600 y seleccione el puerto serial para una comunicación efectiva con el Arduino.</li>
                <li>Ingrese las constantes de masa y radio en las secciones correspondientes de la interfaz para el experimento.</li>
                <li>Configure el temporizador con la duración deseada para garantizar la ejecución del experimento durante el tiempo específico necesario.</li>
                <li>Al finalizar el ensayo, exporte los datos utilizando la función de exportación en formatos como CSV, Excel o TXT.</li>
                <li>Reinicie las gráficas antes de realizar otra prueba para evitar interferencias con datos anteriores.</li>
                <li>Desconéctese del Arduino de manera segura al finalizar todas las pruebas clicando en "desconectar" para mantener un ambiente controlado.</li>
            </ol>
        </div>
        <div>
            <b>Precauciones:</b>
            <ul>
                <li>Puede pausar, reiniciar o detener la recepción de datos en cualquier momento.</li>
                <li>Exporte datos haciendo clic en "Exportar Datos".</li>
            </ul>
        </div>
        <div>
            <b>Riesgo y peligros prioritarios:</b>
            <ul>
                <li>Mecanicos: Uso de herramientas y equipos: proyeccion de particulas o cortes.</li>
                <li>Condiciones de seguridad: Cableado desordenado y expuesto por las areas de circulacion.</li>
                <li>Condiciones de almacenamiento: Orden y organizacion de los equipos.</li>
                <li>Biomecanico: Permanencia en posicion bipeda y manipulacion manual de cargas.</li>
            </ul>
        </div>
        <div style="color: red; font-weight: bold; text-align: center;">
            <p>IMPORTANTE: CADA VEZ QUE SE VAYA A REALIZAR UNA PRUEBA, DEBE DEJAR EL PIN SIN LAS MASAS CON 10 SEG INICIADOS EN EL TEMPORIZADOR SIN INICIAR EL TRIBOMETRO PIN ON DISK Y VERIFICAR QUE TODOS LOS SENSORES ESTÉN ENVIANDO DATOS. SOLO DESPUÉS DE ESO, COLOQUE LAS RESPECTIVAS MASAS Y INICIE LA MAQUINA.</p>
        </div>
    </body>
</html>
            """
        mensaje.setText(texto)
        mensaje.exec_()

    def actualizar_variable1(self, nuevo_valor):
        self.mi_variable1 = nuevo_valor
        print(f"Valor actual de mi_variable1: {self.mi_variable1}")

    def actualizar_variable2(self, nuevo_valor):
        self.mi_variable2 = nuevo_valor
        print(f"Valor actual de mi_variable2: {self.mi_variable2}")

    def show_timer_dialog(self):
        dialog = TimerDialog(self)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            self.time_required = dialog.time_edit.time()
            self.remaining_time = self.time_required
            self.update_timer_display()

    def start_temporizador(self):
        if self.remaining_time > QTime(0, 0):
            self.timer.start(1000)  # Inicia el temporizador con actualización cada 1000 ms (1 segundo)

    def start_receiving_data(self):
        self.serial.open(QIODevice.ReadWrite)
        print(self.serial.isOpen())
        if self.serial.isOpen():
            self.timer.stop()  # Detiene el temporizador antes de iniciar la recepción
            self.serial.readyRead.connect(self.read_data)
            print("Iniciando recepción de datos.")
            counter = 0
            while counter >= 5000000:
                counter = counter + 1
            if self.remaining_time > QTime(0, 0):
                self.ultimoTiempo = self.remaining_time.elapsed()
                self.timer.start(1000)  # Inicia el temporizador si se ha configurado
        else:
            print("No se puede iniciar la recepción de datos sin una conexión activa.")

    def pause_temporizador(self):
        self.timer.stop()

    def reset_temporizador(self):
        self.timer.stop()
        self.remaining_time = QTime(0, 0)
        self.time_required = QTime(0, 0)
        self.update_timer_display()

    def reset_graficas(self):
        self.data_history = {
            'var1': [],
            'var2': [],
            'var3': [],
            'var4': []
        }

        self.plt_1.clear()
        self.plt_2.clear()
        self.plt_3.clear()
        self.plt_4.clear()

        if self.timer.isActive():
            self.timer.stop()
            self.remaining_time = self.time_required
            self.update_timer_display()

    def read_ports(self):
        self.baudrates = ['9600']
        portList = []
        ports = QSerialPortInfo().availablePorts()
        for i in ports:
            portList.append(i.portName())
        self.ui.cb_list_ports.clear()
        self.ui.cb_list_baudrates.clear()
        self.ui.cb_list_ports.addItems(portList)
        self.ui.cb_list_baudrates.addItems(self.baudrates)
        self.ui.cb_list_baudrates.setCurrentText("9600")

    def serial_connect(self):
        self.port = self.ui.cb_list_ports.currentText()
        self.baud = self.ui.cb_list_baudrates.currentText()
        self.serial.setBaudRate(int(self.baud))
        self.serial.setPortName(self.port)
        if self.serial.open(QIODevice.ReadWrite):
            self.ui.bt_connect.setEnabled(False)
            print(f"Conexión establecida en el puerto {self.port} a {self.baud} baud.")
            self.serial.close()
            self.reset_graficas()
        else:
            print("No se pudo establecer la conexión.")

    def serial_disconnect(self):
        print("Desconectando...")
        self.ui.bt_connect.setEnabled(True)
        self.serial.close()
        self.pause_temporizador()
        self.update()
        print("Desconexión completada")

    def read_data(self):
        if self.timer.isActive():
            if not self.serial.canReadLine() or self.remaining_time <= QTime(0, 0):
                return
            if self.serial.bytesAvailable() > 0:
                rx = self.serial.readLine()
                data = str(rx, 'utf-8').strip().split('|')
            if len(data) == 4 and self.tiempo - self.ultimoTiempo >= 1000:
                self.ultimoTiempo = self.remaining_time.elapsed()
                self.data_history['var1'].append(float(data[0]))
                self.data_history['var2'].append(float(data[1]))
                self.data_history['var3'].append(float(data[2]) * (self.mi_variable2 / 1000))
                self.data_history['var4'].append(float(data[3]) / (self.mi_variable1 * 1000))

                max_history_len = 36000

                if len(self.data_history['var1']) > max_history_len:
                    self.data_history['var1'].pop(0)
                    self.data_history['var2'].pop(0)
                    self.data_history['var3'].pop(0)
                    self.data_history['var4'].pop(0)

                start_index = max(0, len(self.data_history['var1']) - self.max_data_len)
                end_index = len(self.data_history['var1'])

                x_data = np.arange(start_index, end_index)

                self.update_plot('var1', x_data, self.data_history['var1'][start_index:end_index])
                self.update_plot('var2', x_data, self.data_history['var2'][start_index:end_index])
                self.update_plot('var3', x_data, self.data_history['var3'][start_index:end_index])
                self.update_plot('var4', x_data, self.data_history['var4'][start_index:end_index])

                if self.remaining_time <= QTime(0, 0):
                    self.serial.close()
                    self.timer.stop()

    def update_plot(self, variable_name, x_data, y_data):
        if variable_name == 'var1':
            self.plt_1.clear()
            self.plt_1.plot(x_data, y_data, pen=pg.mkPen('#03078c', width=2))
        elif variable_name == 'var2':
            self.plt_2.clear()
            self.plt_2.plot(x_data, y_data, pen=pg.mkPen('#03078c', width=2))
        elif variable_name == 'var3':
            self.plt_3.clear()
            self.plt_3.plot(x_data, y_data, pen=pg.mkPen('#03078c', width=2))
        elif variable_name == 'var4':
            self.plt_4.clear()
            self.plt_4.plot(x_data, y_data, pen=pg.mkPen('#03078c', width=2))

    def exportar_a_excel(self, file_path):
        end_index = len(self.data_history['var1'])
        data = {
            'Tiempo': np.arange(0, end_index),
            'Humedad': self.data_history['var1'],
            'Temperatura': self.data_history['var2'],
            'Distancia': self.data_history['var3'],
            'Friccion': self.data_history['var4']
        }
        df = pd.DataFrame(data)

        workbook = Workbook()
        sheet = workbook.active

        sheet.append(['Tiempo', 'Humedad', 'Temperatura', 'Distancia', 'Friccion'])

        for row in df.itertuples(index=False):
            sheet.append(row)

        workbook.save(file_path)

    def exportar_a_txt(self, file_path):
        end_index = len(self.data_history['var1'])
        Tiempo = np.arange(0, end_index)
        with open(file_path, 'w') as txtfile:
            txtfile.write("Tiempo\tHumedad\tTemperatura\tDistancia\tFriccion\n")
            max_length = max(len(self.data_history['var1']), len(self.data_history['var2']),
                             len(self.data_history['var3']), len(self.data_history['var4']))
            for i in range(max_length):
                txtfile.write(
                    f"{Tiempo[i]}\t{self.data_history['var1'][i]}\t{self.data_history['var2'][i]}\t{self.data_history['var3'][i]}\t{self.data_history['var4'][i]}\n")

    def exportar_a_csv(self, file_path):
        end_index = len(self.data_history['var1'])
        Tiempo = np.arange(0, end_index)
        with open(file_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['Tiempo', 'Humedad', 'Temperatura', 'Distancia', 'Friccion'])
            max_length = max(len(self.data_history['var1']), len(self.data_history['var2']),
                             len(self.data_history['var3']), len(self.data_history['var4']))
            for i in range(max_length):
                csv_writer.writerow(
                    [Tiempo[i], self.data_history['var1'][i], self.data_history['var2'][i],
                     self.data_history['var3'][i], self.data_history['var4'][i]])

    def update_timer(self):
        if self.remaining_time > QTime(0, 0):
            self.tiempo = self.remaining_time.elapsed() + 300
            self.remaining_time = self.remaining_time.addSecs(-1)
            self.update_timer_display()
        else:
            self.timer.stop()

    def update_timer_display(self):
        formatted_time = self.remaining_time.toString("HH:mm:ss")
        self.ui.lcdCronometro.display(formatted_time)

    def exportar_datos(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly

        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo", "",
                                                   "Archivos CSV (*.csv);;Archivos de Texto (*.txt);;Archivos XLSX (*.xlsx)",
                                                   options=options)

        if file_path:
            if file_path.endswith(".csv"):
                self.exportar_a_csv(file_path)
            elif file_path.endswith(".txt"):
                self.exportar_a_txt(file_path)
            elif file_path.endswith(".xlsx"):
                self.exportar_a_excel(file_path)

    def send_data(self, data):
        data = data + "\n"
        print(data)
        if self.serial.isOpen() and self.timer.isActive():
            self.serial.write(data.encode())
        else:
            print("No se pueden enviar datos sin una conexión activa o antes de iniciar la recepción.")

    def control_bt_normal(self):
        self.showNormal()
        self.ui.bt_normal.hide()
        self.ui.bt_maximize.show()

    def control_bt_maximize(self):
        self.showMaximized()
        self.ui.bt_maximize.hide()
        self.ui.bt_normal.show()

    def resizeEvent(self, event):
        rect = self.rect()
        self.ui.grip.move(rect.right() - self.ui.gripSize, rect.bottom() - self.ui.gripSize)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_start_position = event.globalPos()
            self.click_posicion = event.pos()

    def mover_ventana(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            if self.drag_start_position is not None:
                self.move(self.pos() + event.globalPos() - self.drag_start_position)
                self.drag_start_position = event.globalPos()

        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
    
