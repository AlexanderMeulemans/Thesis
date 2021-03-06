import time

import numpy as np
import torch

import utils.helper_functions as hf
from depreciated.tensorboard_api import Tensorboard
from layers.invertible_layer import InvertibleInputLayer, \
    InvertibleLeakyReluLayer, InvertibleLinearOutputLayer, InvertibleNetwork
from layers.layer import Layer, LeakyReluLayer, InputLayer, LinearOutputLayer, \
    Network
from optimizers.optimizers import SGD
from utils.create_datasets import GenerateDatasetFromModel

# torch.manual_seed(42)

# ======== set log directory ==========
log_dir = 'logs_hiddenlayer'
hf.init_logdir(log_dir)
Layer.tensorboard = Tensorboard(log_dir)

if torch.cuda.is_available():
    nb_gpus = torch.cuda.device_count()
    gpu_idx = nb_gpus - 1
    device = torch.device("cuda:{}".format(gpu_idx))
    torch.set_default_tensor_type('torch.cuda.FloatTensor')
    print('using GPU')
else:
    device = torch.device("cpu")
    print('using CPU')

# Create toy model dataset

input_layer_true = InvertibleInputLayer(layer_dim=6, out_dim=5,
                                        loss_function='mse',
                                        name='input_layer_truemodel')
hidden_layer_true = InvertibleLeakyReluLayer(negative_slope=0.01, in_dim=6,
                                             layer_dim=5, out_dim=4,
                                             loss_function='mse',
                                             name='hidden_layer_truemodel')
output_layer_true = InvertibleLinearOutputLayer(inDim=5, layerDim=4,
                                                stepsize=0.01,
                                                name='output_layer_truemodel')

true_network = InvertibleNetwork([input_layer_true, hidden_layer_true,
                                  output_layer_true])

generator = GenerateDatasetFromModel(true_network)

input_dataset, output_dataset = generator.generate(7000, 1)
input_dataset_test, output_dataset_test = generator.generate(1, 1000)

# compute least squares solution as control
print('computing LS solution ...')
input_dataset_np = input_dataset.cpu().numpy()
output_dataset_np = output_dataset.cpu().numpy()
input_dataset_test_np = input_dataset_test.cpu().numpy()
output_dataset_test_np = output_dataset_test.cpu().numpy()

input_dataset_np = np.reshape(input_dataset_np, (input_dataset_np.shape[0] * \
                                                 input_dataset_np.shape[1],
                                                 input_dataset_np.shape[2]))
output_dataset_np = np.reshape(output_dataset_np, (output_dataset_np.shape[0] * \
                                                   output_dataset_np.shape[1],
                                                   output_dataset_np.shape[2]))
input_dataset_test_np = np.reshape(input_dataset_test_np,
                                   (input_dataset_test_np.shape[0] * \
                                    input_dataset_test_np.shape[1],
                                    input_dataset_test_np.shape[2]))
output_dataset_test_np = np.reshape(output_dataset_test_np,
                                    (output_dataset_test_np.shape[0] * \
                                     output_dataset_test_np.shape[1],
                                     output_dataset_test_np.shape[2]))

weights = np.linalg.lstsq(input_dataset_np, output_dataset_np)
print('mean residuals: ' + str(np.mean(weights[1])))
weights = weights[0]
train_loss = np.mean(np.sum(np.square(np.matmul(input_dataset_np, weights) \
                                      - output_dataset_np), axis=1))
test_loss = np.mean(np.sum(np.square(np.matmul(input_dataset_test_np, weights) \
                                     - output_dataset_test_np), axis=1))
print('LS train loss: ' + str(train_loss))
print('LS test loss: ' + str(test_loss))

# Creating training network
inputlayer = InvertibleInputLayer(layer_dim=6, out_dim=5, loss_function='mse',
                                  name='input_layer')
hiddenlayer = InvertibleLeakyReluLayer(negative_slope=0.01, in_dim=6,
                                       layer_dim=5, out_dim=4, loss_function=
                                       'mse',
                                       name='hidden_layer')
outputlayer = InvertibleLinearOutputLayer(inDim=5, layerDim=4,
                                          stepsize=0.01,
                                          name='output_layer')

network = InvertibleNetwork([inputlayer, hiddenlayer, outputlayer])

# Initializing optimizer
optimizer1 = SGD(network=network, threshold=0.0001, init_learning_rate=0.1,
                 tau=100,
                 final_learning_rate=0.005, compute_accuracies=False, max_epoch=120,
                 outputfile_name='resultfile.csv')

# Train on dataset
timings = np.array([])
start_time = time.time()
optimizer1.run_dataset(input_dataset, output_dataset, input_dataset_test,
                       output_dataset_test)
end_time = time.time()
print('Elapsed time: {} seconds'.format(end_time - start_time))
timings = np.append(timings, end_time - start_time)

# ======== Run same experiment on shallow network ======
# creating separate logdir
log_dir = 'logs_shallow'
hf.init_logdir(log_dir)
Layer.tensorboard = Tensorboard(log_dir)

# Creating training network

inputlayer_shallow = InvertibleInputLayer(layer_dim=6, out_dim=4,
                                          loss_function='mse',
                                          name='input_layer')

outputlayer_shallow = InvertibleLinearOutputLayer(inDim=6, layerDim=4,
                                                  stepsize=0.01,
                                                  name='output_layer')

network_shallow = InvertibleNetwork([inputlayer_shallow, outputlayer_shallow])
optimizer3 = SGD(network=network_shallow, threshold=0.0001,
                 init_learning_rate=0.1,
                 tau=100,
                 final_learning_rate=0.005, compute_accuracies=False, max_epoch=120,
                 outputfile_name='resultfile_shallow.csv')

start_time = time.time()
optimizer3.run_dataset(input_dataset, output_dataset, input_dataset_test,
                       output_dataset_test)
end_time = time.time()
print('Elapsed time: {} seconds'.format(end_time - start_time))
timings = np.append(timings, end_time - start_time)

# ===== Run same experiment with backprop =======

# Creating training network
inputlayer = InputLayer(layer_dim=6, name='input_layer_BP')
hiddenlayer = LeakyReluLayer(negative_slope=0.01, in_dim=6,
                             layer_dim=5,
                             name='hidden_layer_BP')
outputlayer = LinearOutputLayer(inDim=5, layerDim=4, lossFunction='mse',
                                name='output_layer_BP')

network_backprop = Network([inputlayer, hiddenlayer, outputlayer])

# Initializing optimizer
optimizer4 = SGD(network=network, threshold=0.0001, init_learning_rate=0.1,
                 tau=100,
                 final_learning_rate=0.005, compute_accuracies=False, max_epoch=120,
                 outputfile_name='resultfile_BP.csv')

# Train on dataset
start_time = time.time()
optimizer4.run_dataset(input_dataset, output_dataset, input_dataset_test,
                       output_dataset_test)
end_time = time.time()
print('Elapsed time: {} seconds'.format(end_time - start_time))
timings = np.append(timings, end_time - start_time)
np.savetxt("timings.csv", timings, delimiter=",")
