# import libraries
import os
import pandas as pd
import numpy as np
import setGPU
from sklearn.preprocessing import MinMaxScaler
from sklearn.externals import joblib
import seaborn as sns
sns.set(color_codes=True)
import matplotlib.pyplot as plt
#%matplotlib inline
import h5py as h5
from gwpy.timeseries import TimeSeries

from numpy.random import seed
from tensorflow import set_random_seed
import tensorflow as tf
tf.logging.set_verbosity(tf.logging.ERROR)

from keras.layers import Input, Dropout, Dense, LSTM, TimeDistributed, RepeatVector
from keras.models import Model
from keras import regularizers
from keras.callbacks import EarlyStopping, ModelCheckpoint
import argparse

from model import autoencoder_model


def main(args):
    outdir = args.outdir
    detector = args.detector
    os.system('mkdir -p %s'%outdir)

    # Load train and test data

    train_start = 1185939456
    num_train = 5
    train_files = [train_start + i*4096 for i in range(num_train)]
    x = np.array([])

    for file in train_files: 
        load = h5.File('/cvmfs/gwosc.osgstorage.org/gwdata/O2/strain.4k/hdf.v1/%s/%s/%s-%s_GWOSC_O2_4KHZ_R1-%s-4096.hdf5'%(detector, str(train_start), detector[0], detector, str(file)))
        x = np.concatenate((x, load['strain']['Strain'][()]), axis=0)


    test_start = 1186988032
    num_test = 1
    test_files = [test_start + (num_train)*4096 + i*4096 for i in range(num_test)]
    y = np.array([])

    for file in test_files: 
        load = h5.File('/cvmfs/gwosc.osgstorage.org/gwdata/O2/strain.4k/hdf.v1/%s/%s/%s-%s_GWOSC_O2_4KHZ_R1-%s-4096.hdf5'%(detector, str(test_start), detector[0], detector, str(file)))
        y = np.concatenate((y, load['strain']['Strain'][()]), axis=0)

    # normalize the data
    scaler = MinMaxScaler()
    X_train = scaler.fit_transform(x.reshape(-1, 1))
    X_test = scaler.transform(y.reshape(-1, 1))
    scaler_filename = "%s/scaler_data_%s"%(outdir, detector)
    joblib.dump(scaler, scaler_filename)

    # reshape inputs for LSTM [samples, timesteps, features]
    X_train = X_train.reshape(X_train.shape[0], 1, X_train.shape[1])
    print("Training data shape:", X_train.shape)
    X_test = X_test.reshape(X_test.shape[0], 1, X_test.shape[1])
    print("Test data shape:", X_test.shape)

    model = autoencoder_model(X_train)
    model.compile(optimizer='adam', loss='mae')
    model.summary()

    # fit the model to the data
    nb_epochs = 100
    batch_size = 2048
    earlyStopping = EarlyStopping(monitor='val_loss', patience=10, verbose=0, mode='min')
    mcp_save = ModelCheckpoint('%s/best_model.hdf5'%(outdir), save_best_only=True, monitor='val_loss', mode='min')
    history = model.fit(X_train, X_train, epochs=nb_epochs, batch_size=batch_size,
                        validation_split=0.2, callbacks=[earlyStopping, mcp_save]).history
    model.save('%s/last_model.hdf5'%(outdir))

    fig, ax = plt.subplots(figsize=(14, 6), dpi=80)
    ax.plot(history['loss'], 'b', label='Train', linewidth=2)
    ax.plot(history['val_loss'], 'r', label='Validation', linewidth=2)
    ax.set_title('Model loss', fontsize=16)
    ax.set_ylabel('Loss (mae)')
    ax.set_xlabel('Epoch')
    ax.legend(loc='upper right')
    plt.savefig('%s/loss.jpg'%(outdir))

if __name__ == "__main__":
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser()
    
    # Required positional arguments
    parser.add_argument("outdir", help="Required output directory")
    parser.add_argument("detector", help="Required output directory")
    
    args = parser.parse_args()
    main(args)

