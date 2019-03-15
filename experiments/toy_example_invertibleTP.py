from utils.create_datasets import GenerateDatasetFromModel
from optimizers.optimizers import SGD
from layers.invertible_layer import InvertibleInputLayer, \
InvertibleLeakyReluLayer, InvertibleLinearOutputLayer
from networks.invertible_network import InvertibleNetwork
from layers.layer import InputLayer, LeakyReluLayer, \
    LinearOutputLayer
from layers.network import Network
import torch
import numpy as np
import time
from tensorboardX import SummaryWriter
from utils.LLS import linear_least_squares
import os

torch.manual_seed(33)

# ======== User variables ============
nb_training_batches = 1000
batch_size = 1
testing_size = 1000

# ======== set log directory ==========
log_dir = '../logs/toyexample_invertible_TP'
writer = SummaryWriter(log_dir=log_dir)

# ======== set device ============
if torch.cuda.is_available():
    gpu_idx = 0
    device = torch.device("cuda:{}".format(gpu_idx))
    # IMPORTANT: set_default_tensor_type uses automatically device 0,
    # untill now, I did not find a fix for this
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    torch.set_default_tensor_type('torch.cuda.FloatTensor')
    print('using GPU')
else:
    device = torch.device("cpu")
    print('using CPU')

# ======== Create toy model dataset =============

input_layer_true = InputLayer(layerDim=5, writer=writer,
                              name='input_layer_true_model')
hidden_layer_true = LeakyReluLayer(negativeSlope=0.3,inDim=5,layerDim=5,
                                   writer=writer,
                                   name='hidden_layer_true_model')
output_layer_true = LinearOutputLayer(inDim=5, layerDim=5,
                                      lossFunction='mse',
                                      writer=writer,
                                      name='output_layer_true_model')
true_network = Network([input_layer_true, hidden_layer_true,
                                  output_layer_true])

generator = GenerateDatasetFromModel(true_network)

input_dataset, output_dataset = generator.generate(nb_training_batches,
                                                   batch_size)
input_dataset_test, output_dataset_test = generator.generate(
    testing_size, 1)

# compute least squares solution as control
print('computing LS solution ...')
weights, train_loss, test_loss = linear_least_squares(input_dataset,
                                                      output_dataset,
                                                      input_dataset_test,
                                                      output_dataset_test)
print('LS train loss: '+str(train_loss))
print('LS test loss: '+str(test_loss))

# ===== Run experiment with invertible TP =======

# Creating training network
inputlayer = InvertibleInputLayer(layerDim=5,outDim=5, lossFunction='mse',
                                  name='input_layer', writer=writer)
hiddenlayer = InvertibleLeakyReluLayer(negativeSlope=0.01, inDim=5,
                                        layerDim=5, outDim=5, lossFunction=
                                        'mse',
                                       name='hidden_layer',
                                       writer=writer)
outputlayer = InvertibleLinearOutputLayer(inDim=5, layerDim=5,
                                              stepsize=0.01,
                                          name='output_layer',
                                          writer=writer)

network = InvertibleNetwork([inputlayer, hiddenlayer, outputlayer])

# Initializing optimizer
optimizer1 = SGD(network=network,threshold=0.001, initLearningRate=0.01,
                 tau= 100,
                finalLearningRate=0.005, computeAccuracies=False,
                 maxEpoch=120,
                 outputfile_name='resultfile.csv')



# Train on dataset
timings = np.array([])
start_time = time.time()
optimizer1.runDataset(input_dataset, output_dataset, input_dataset_test,
                      output_dataset_test)
end_time = time.time()
print('Elapsed time: {} seconds'.format(end_time-start_time))
timings = np.append(timings, end_time-start_time)