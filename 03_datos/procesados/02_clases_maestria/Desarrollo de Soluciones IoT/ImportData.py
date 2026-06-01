import numpy as np
import matplotlib.pyplot as plt

############################ Cargar señales medidas #######################     
with open('DataSet.npy', 'rb') as f:
    p  = np.load(f)
    t  = np.load(f)
    ts = np.load(f)
    
###################### Mostrar figuras ######################
for i in range(p.shape[0]):
     plt.plot(t,p[i,:],label='data'+str(i+1))
     
plt.xlabel('Tiempo [s]')
plt.grid()    
plt.legend(loc='upper left')
plt.show()
    
