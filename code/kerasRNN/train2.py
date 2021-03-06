'''
This script trains model2_1 (RNN + deep NN on basic linear features and previous week data),
makes predictions and analises them
'''


import os
import sys
import gc
import copy
import numpy as np
from keras.preprocessing.image import ImageDataGenerator

from model2_1 import get_model, model_data
import json

from config import *
import matplotlib.pyplot as plt



train_file = "data/energy/preprocess/train.npy"
test_file = "data/energy/preprocess/test.npy"

output_losses_file = "output/kerasRNN/hiddenX2/losses.csv"
output_weights_best_file = "output/kerasRNN/hiddenX2/weights_best.hdf5"
output_weights_file = "output/kerasRNN/hiddenX2/weights.hdf5"
nRNNHidden = (N_ZONES+N_TEMPS)*2

if len(sys.argv)>1:
    continue_training = json.loads(sys.argv[1].lower())
else:
    continue_training = False # systole or diastole

print("Continue_training = %d" % (continue_training))

def split_data(data, split_ratio):
    '''
     Split data into training and validation seets.
     '''
    np.random.seed(12345)
    N = len(data)
    idx = np.arange(N)
    idx_test = np.random.choice(idx, size=int(np.floor(N * split_ratio)),replace=False)
    idx_train = np.setdiff1d(idx, idx_test, assume_unique=True)
    train = [data[i] for i in idx_train]
    test = [data[i] for i in idx_test]
    return train,test


def plot(Y,Y_pred,i=0,iZone=0):
    '''
    Plot one week loads for a particular zone. Observed and predicted.
    '''
    n = N_HOURS*7
    plt.plot(range(n),Y[i*n:(i+1)*n,iZone])
    plt.plot(range(n),Y_pred[i*n:(i+1)*n,iZone])

    for j in range(n):
        print Y[i*n+j,0], Y_pred[i*n+j,0]

    plt.show()


def train(continue_training=False):
    '''
      Run training
    '''
    print('Loading training data...')
    train = np.load(train_file)
    train,val = split_data(train, split_ratio = 0.2)
    test = np.load(test_file)
    print "done."

    print('Prepare data...')
    input_train = model_data(train)
    input_val = model_data(val)
    input_test = model_data(test)
    nFeatures = input_train["X_input"].shape[1]
    nTin = input_train["RNN_input"].shape[1]
    nRNNFeatures = input_train["RNN_input"].shape[2]
    print "using %d/%d/%d samples with %d features %d timesteps %d RNN features %d RNN hidden" % \
          (input_train["X_input"].shape[0],input_val["X_input"].shape[0],input_test["X_input"].shape[0], \
           nFeatures,nTin,nRNNFeatures,nRNNHidden)

    print('Loading and compiling models...')
    model = get_model(nTin=nTin, nRNNFeatures=nRNNFeatures,nRNNHidden=nRNNHidden, nFeatures=nFeatures, nOutput=N_ZONES)
    if continue_training:
        print('Loading models weights...')
        model.load_weights(output_weights_best_file)
    print "done."

    print('-'*50)
    print('Training model...')
    print('-'*50)
    nIterations  = 300
    epochs_per_iter = 1
    batch_size = 64 # 1024 # 64
    loss_val_min = sys.float_info.max

    losses_train = []
    losses_val = []
    losses_test = []
    errors_train = []
    errors_val = []
    errors_test = []

    for iIteration in range(nIterations):
        print('-'*50)
        print('Iteration {0}/{1}'.format(iIteration + 1,nIterations))
        print('-'*50)

        print('Fitting model...')
        hist = model.fit(input_train, validation_data=(input_val), \
                         shuffle=True, nb_epoch=epochs_per_iter, verbose=1,batch_size=batch_size)
        loss_train = hist.history['loss'][-1]
        loss_val = hist.history['val_loss'][-1]
        losses_train.append(loss_train)
        losses_val.append(loss_val)
        print("Loss train/test  = %f / %f" % (loss_train, loss_val))


        print('Calculate predictions...')
        Ypred_train = model.predict(input_train, batch_size=batch_size, verbose=1)["out"]
        Ypred_val = model.predict(input_val, batch_size=batch_size, verbose=1)["out"]
        Ypred_test = model.predict(input_test, batch_size=batch_size, verbose=1)["out"]
        Y_train = input_train["out"]
        Y_val = input_val["out"]
        Y_test = input_test["out"]
        error_train = np.sqrt(np.mean((Y_train - Ypred_train) * (Y_train - Ypred_train))) / np.mean(Y_train)
        error_val  = np.sqrt(np.mean((Y_val - Ypred_val) * (Y_val - Ypred_val))) / np.mean(Y_val)
        error_test  = np.sqrt(np.mean((Y_test - Ypred_test) * (Y_test - Ypred_test))) / np.mean(Y_test)
        errors_train.append(error_train)
        errors_val.append(error_val)
        errors_test.append(error_test)
        print("Error train/val/test = %f / %f / %f" % (error_train, error_val, error_test))
        print "done."



        print('Save Losses...')
        csv_file = open(output_losses_file, "w")
        csv_file.write("iter,train_loss,test_loss,train_error,val_error,test_error\n")
        for i in range(len(losses_train)):
            csv_file.write("%d,%f,%f,%f,%f,%f\n" % (i, losses_train[i], losses_val[i],\
                                                    errors_train[i],errors_val[i],errors_test[i]))
        csv_file.close()
        print "done."

        print('Saving weights...')
        model.save_weights(output_weights_file, overwrite=True)
        if loss_val < loss_val_min:
            loss_val_min = loss_val
            model.save_weights(output_weights_best_file, overwrite=True)
        print "done."

        # force deletion
        del hist
        model.training_data = None
        model.validation_data = None
        gc.collect()

    print "Plot example..."
    plot(Y_val,Ypred_val,i=0,iZone=0)
    print "done."


    print "END."

# TODO: change as needed
if __name__ == "__main__":
    os.chdir("../../")
    train(continue_training=continue_training)

