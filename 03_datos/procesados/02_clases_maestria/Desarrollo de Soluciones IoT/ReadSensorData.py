from pyArduino import *
import matplotlib.pyplot as plt

ts = 0.1 # Tiempo de muestreo
tf = 10  # Tiempo de lectura de datos
t = np.arange(0,tf+ts,ts) # Array de tiempo
N = len(t) # Numero de muestras

######################## Comunicacion Serial ###############

port = 'COM5'  # Com Arduino
baudRate = 9600 # Baudios
sizeData = 6

arduino = serialArduino(port,baudRate,sizeData)# Objeto serial

arduino.readSerialStart() # Inicia lectura de datos

################# Inicializacion de Datos ###################
p =  np.zeros((sizeData,N))

########################## Loop ########################

for k in range(N):

     start_time = time.time() # Tiempo actual
     
     for i in range(sizeData):
          p[i][k] = arduino.rawData[i]
          
     elapsed_time = time.time() - start_time # Tiempo transcurrido
     
     time.sleep(ts-elapsed_time) # Esperar hasta completar el tiempo de muestreo
         
arduino.close() # Cerrar puerto serial

######################## Guardar datos ###########################
with open('DataSet.npy', 'wb') as f:
     np.save(f,p)
     np.save(f,t)
     np.save(f,ts)
     
###################### Mostrar figuras ######################
for i in range(sizeData):
     plt.plot(t,p[i,:],label='data'+str(i+1))
     
plt.xlabel('Tiempo [s]')
plt.grid()    
plt.legend(loc='upper left')
plt.show()
