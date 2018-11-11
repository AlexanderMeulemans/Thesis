import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import HelperClasses as hc
import HelperFunctions as hf
from HelperClasses import NetworkError

class Layer(object):
    """ Parent class of all occuring layers in neural networks with only feedforward weights.
    This class should not be used directly, only via its children"""

    def __init__(self, inDim, layerDim):
        """
        Initializes the Layer object
        :param inDim: input dimension of the layer (equal to the layer dimension of the previous layer in the network)
        :param layerDim: Layer dimension
        """
        self.setLayerDim(layerDim)
        self.setInDim(inDim)
        self.initParameters()

    def setLayerDim(self,layerDim):
        if not isinstance(layerDim,int):
            raise TypeError("Expecting an integer layer dimension")
        if layerDim <= 0:
            raise ValueError("Expecting strictly positive layer dimension")
        self.layerDim = layerDim

    def setInDim(self,inDim):
        if not isinstance(inDim,int):
            raise TypeError("Expecting an integer layer dimension")
        if inDim <= 0:
            raise ValueError("Expecting strictly positive layer dimension")
        self.inDim = inDim

    def setForwardParameters(self, forwardWeights, forwardBias):
        if not isinstance(forwardWeights, torch.Tensor):
            raise TypeError("Expecting a tensor object for self.forwardWeights")
        if not isinstance(forwardBias, torch.Tensor):
            raise TypeError("Expecting a tensor object for self.forwardBias")
        if hf.containsNaNs(forwardWeights):
            raise ValueError("forwardWeights contains NaNs")
        if hf.containsNaNs(forwardBias):
            raise ValueError("forwardBias contains NaNs")
        if not forwardWeights.shape == self.forwardWeights.shape:
            raise ValueError("forwardWeights has not the correct shape")
        if not forwardBias.shape == self.forwardBias.shape:
            raise ValueError("forwardBias has not the correct shape")

        self.forwardWeights = forwardWeights
        self.forwardBias = forwardBias

    def setForwardGradients(self, forwardWeightsGrad, forwardBiasGrad):
        if not isinstance(forwardWeightsGrad, torch.Tensor):
            raise TypeError("Expecting a tensor object for self.forwardWeightsGrad")
        if not isinstance(forwardBiasGrad, torch.Tensor):
            raise TypeError("Expecting a tensor object for self.forwardBiasGrad")
        if hf.containsNaNs(forwardWeightsGrad):
            raise ValueError("forwardWeightsGrad contains NaNs")
        if hf.containsNaNs(forwardBiasGrad):
            raise ValueError("forwardBias contains NaNs")
        if not forwardWeightsGrad.shape == self.forwardWeightsGrad.shape:
            raise ValueError("forwardWeightsGrad has not the correct shape")
        if not forwardBiasGrad.shape == self.forwardBiasGrad.shape:
            raise ValueError("forwardBiasGrad has not the correct shape")

        self.forwardWeightsGrad = forwardWeightsGrad
        self.forwardBiasGrad = forwardBiasGrad

    def setForwardOutput(self,forwardOutput):
        if not isinstance(forwardOutput, torch.Tensor):
            raise TypeError("Expecting a tensor object for self.forwardOutput")
        if not forwardOutput.shape(-2) == self.layerDim:
            raise ValueError("Expecting same dimension as layerDim")
        if not forwardOutput.shape(-1) == 1:
            raise ValueError("Expecting same dimension as layerDim")
        self.forwardOutput = forwardOutput

    def setBackwardOutput(self,backwardOutput):
        if not isinstance(backwardOutput, torch.Tensor):
            raise TypeError("Expecting a tensor object for self.backwardOutput")
        if not backwardOutput.shape(-2) == self.layerDim:
            raise ValueError("Expecting same dimension as layerDim")
        if not backwardOutput.shape(-1) == 1:
            raise ValueError("Expecting same dimension as layerDim")
        self.backwardOutput = backwardOutput

    def initParameters(self):
        """ Initializes the layer parameters when the layer is created. This method should only be used when creating
        a new layer. Use setForwardParameters to update the parameters and computeGradient to update the gradients"""
        self.forwardWeights = torch.rand(self.layerDim, self.inDim)
        self.forwardBias = torch.zeros(self.layerDim, 1)
        self.forwardWeightsGrad = torch.zeros(self.layerDim, self.inDim)
        self.forwardBiasGrad = torch.zeros(self.layerDim, 1)


    def zeroGrad(self):
        """ Set the gradients of the layer parameters to zero """
        self.forwardWeightsGrad = torch.zeros(self.layerDim, self.inDim)
        self.forwardBiasGrad = torch.zeros(self.layerDim,1)

    def updateForwardParameters(self, learningRate):
        """
        Update the forward weights and bias of the layer using the computed gradients
        :param learningRate: Learning rate of the layer
        """
        if not isinstance(learningRate,float):
            raise TypeError("Expecting a float number as learningRate")
        if learningRate <= 0.:
            raise ValueError("Expecting a strictly positive learningRate")

        forwardWeights = self.forwardWeights - torch.mul(self.forwardWeightsGrad, learningRate)
        forwardBias = self.forwardBias - torch.mul(self.forwardBiasGrad, learningRate)
        self.setForwardParameters(forwardWeights, forwardBias)

    def propagateForward(self,lowerLayer):
        """
        :param lowerLayer: The first layer upstream of the layer 'self'
        :type lowerLayer: Layer
        :return saves the computed output of the layer to self.forwardOutput.
                forwardOutput is a 3D tensor of size batchDimension x layerDimension x 1
        """
        if not isinstance(lowerLayer,Layer):
            raise TypeError("Expecting a Layer object as argument for propagateForward")
        if not lowerLayer.layerDim == self.inDim:
            raise ValueError("Layer sizes are not compatible for propagating forward")

        self.forwardInput = lowerLayer.forwardOutput
        self.linearActivation = torch.matmul(self.forwardWeights,self.forwardInput) + self.forwardBias
        self.forwardOutput = self.nonlinearity(self.linearActivation)

    def nonlinearity(self,linearActivation):
        """ This method should be always overwritten by the children"""
        raise NetworkError("The method nonlinearity should always be overwritten by children of Layer. Layer on itself "
                        "cannot be used in a network")

    def computeGradients(self, lowerLayer):
        """
        :param lowerLayer: first layer upstream of the layer self
        :type lowerLayer: Layer
        :return: saves the gradients of the cost function to the layer parameters for all the batch samples

        """

        weight_gradients = torch.matmul(self.backwardOutput,torch.transpose(lowerLayer.forwardOutput,-1,-2))
        bias_gradients = self.backwardOutput
        self.setForwardGradients(torch.mean(weight_gradients, 0),torch.mean(bias_gradients, 0))


class ReluLayer(Layer):
    """ Layer of a neural network with a RELU activation function"""

    def nonlinearity(self,linearActivation):
        """ Returns the nonlinear activation of the layer"""
        return F.relu(linearActivation)

    def propagateBackward(self,upperLayer):
        """
        :param upperLayer: the layer one step downstream of the layer 'self'
        :type upperLayer: Layer
        :return: saves the backwards output in self. backwardOutput is of size batchDimension x layerdimension  x 1
        """
        if not isinstance(upperLayer,Layer):
            raise TypeError("Expecting a Layer object as argument for propagateBackward")
        if not upperLayer.inDim == self.layerDim:
            raise ValueError("Layer sizes are not compatible for propagating backwards")

        self.backwardInput = upperLayer.backwardOutput
        # Construct vectorized Jacobian for all batch samples.
        activationDer = torch.tensor([[[1.] if self.linearActivation[i,j,0]>0 else [0.]
                            for j in range(self.linearActivation.size(1))]
                            for i in range(self.linearActivation.size(0))])
        backwardOutput = torch.mul(torch.matmul(torch.transpose(upperLayer.forwardWeights,-1,-2),
                                                     self.backwardInput),activationDer)
        self.setBackwardOutput(backwardOutput)


class SoftmaxLayer(Layer):
    """ Layer of a neural network with a Softmax activation function"""

    def nonlinearity(self,linearActivation):
        """ Returns the nonlinear activation of the layer"""
        softmax = torch.nn.Softmax(1)
        return softmax(linearActivation)

    def propagateBackward(self,upperLayer):
        """
        :param upperLayer: the layer one step downstream of the layer 'self'
        :type upperLayer: Layer
        :return: saves the backwards output in self. backwardOutput is of size batchDimension x layerdimension  x 1
        """
        if not isinstance(upperLayer,Layer):
            raise TypeError("Expecting a Layer object as argument for propagateBackward")
        if not upperLayer.inDim == self.layerDim:
            raise ValueError("Layer sizes are not compatible for propagating backwards")

        self.backwardInput = upperLayer.backwardOutput
        # Construct Jacobian for all batch samples.
        softmaxActivations = self.forwardOutput
        jacobian = torch.tensor([[[softmaxActivations[i, j, 0] * (hf.kronecker(j, k) - softmaxActivations[i, k, 0])
                                        for k in range(softmaxActivations.size(1))]
                                       for j in range(softmaxActivations.size(1))]
                                      for i in range(softmaxActivations.size(0))])
        backwardOutput = torch.matmul(torch.transpose(jacobian, -1, -2),
                                           torch.matmul(torch.transpose(upperLayer.forwardWeights, -1, -2)
                                                        , self.backwardInput))
        self.setBackwardOutput(backwardOutput)

class LinearLayer(Layer):
    """ Layer of a neural network with a linear activation function"""

    def nonlinearity(self,linearActivation):
        """ Returns the nonlinear activation of the layer"""
        return linearActivation

    def propagateBackward(self,upperLayer):
        """
        :param upperLayer: the layer one step downstream of the layer 'self'
        :type upperLayer: Layer
        :return: saves the backwards output in self. backwardOutput is of size batchDimension x layerdimension  x 1
        """
        if not isinstance(upperLayer,Layer):
            raise TypeError("Expecting a Layer object as argument for propagateBackward")
        if not upperLayer.inDim == self.layerDim:
            raise ValueError("Layer sizes are not compatible for propagating backwards")

        self.backwardInput = upperLayer.backwardOutput
        backwardOutput = torch.matmul(torch.transpose(upperLayer.forwardWeights, -1, -2), self.backwardInput)
        self.setBackwardOutput(backwardOutput)

class InputLayer(Layer):
    """ Input layer of the neural network, e.g. the pixelvalues of a picture. """

    def __init__(self,layerDim):
        """ InputLayer has only a layerDim and a forward activation that can be set,
         no input dimension nor parameters"""
        self.setLayerDim(layerDim)


    def propagateForward(self, lowerLayer):
        """ This function should never be called for an input layer, the forwardOutput should be directly set
        to the input values of the network (e.g. the pixel values of a picture) """
        raise NetworkError("The forwardOutput should be directly set to the input values of the network for "
                           "an InputLayer")

    def propagateBackward(self, upperLayer):
        """ This function should never be called for an input layer, there is no point in having a backward output
         here, as this layer has no parameters to update"""
        raise NetworkError("Propagate Backward should never be called for an input layer, there is no point in having "
                           "a backward output here, as this layer has no parameters to update")

class OutputLayer(Layer):
    """" Super class for the last layer of a network. This layer has a loss as extra attribute and some extra
    methods as explained below. """

    def __init__(self,inDim, layerDim, lossFunction):
        """
        :param inDim: input dimension of the layer, equal to the layer dimension of the second last layer in the network
        :param layerDim: Layer dimension
        :param loss: string indicating which loss function is used to compute the network loss
        """
        super().__init__(inDim, layerDim)
        self.setLossFunction(lossFunction)

    def setLossFunction(self,lossFunction):
        if not isinstance(lossFunction, str):
            raise TypeError('Expecting a string as indicator for the loss function')
        if not (lossFunction == 'mse' or lossFunction == 'crossEntropy'):
            raise NetworkError('Expecting an mse or crossEntropy loss')
        self.lossFunction = lossFunction

    def loss(self,target):
        """ Compute the loss with respect to the target
        :param target: 3D tensor of size batchdimension x class dimension x 1
        """
        if not isinstance(target,torch.Tensor):
            raise TypeError("Expecting a torch.Tensor object as target")
        if not self.forwardOutput.shape == target.shape:
            raise ValueError('Expecting a tensor of dimensions: batchdimension x class dimension x 1. Given target'
                             'has shape' + str(target.shape))
        if self.lossFunction == 'crossEntropy':
            # Convert output 'class probabilities' to one class per batch sample (with highest class probability)
            target_classes = hf.prob2class(target)
            lossFunction = nn.CrossEntropyLoss()
            return lossFunction(self.forwardOutput.squeeze(), target_classes)
        elif self.lossFunction == 'mse':
            lossFunction = nn.MSELoss()
            return lossFunction(self.forwardOutput.squeeze(), target.squeeze())

    def propagateBackward(self, upperLayer):
        """ This function should never be called for an output layer, the backwardOutput should be set based on the
        loss of the layer with computeBackwardOutput"""
        raise NetworkError("Propagate Backward should never be called for an output layer, use computeBackwardOutput "
                           "instead")


class SoftmaxOutputLayer(OutputLayer):
    """ Output layer with a softmax activation function. This layer should always be combined with a crossEntropy
    loss."""

    def nonlinearity(self,linearActivation):
        """ Returns the nonlinear activation of the layer"""
        softmax = torch.nn.Softmax(1)
        return softmax(linearActivation)

    def computeBackwardOutput(self,target):
        """ Compute the backward output based on the derivative of the loss to the linear activation of this layer"""
        if not self.lossFunction == 'crossEntropy':
            raise NetworkError("a softmax output layer should always be combined with a cross entropy loss")
        if not isinstance(target,torch.Tensor):
            raise TypeError("Expecting a torch.Tensor object as target")
        if not self.forwardOutput.shape == target.shape:
            raise ValueError('Expecting a tensor of dimensions: batchdimension x class dimension x 1. Given target'
                             'has shape' + str(target.shape))
        
        backwardOutput = self.forwardOutput - target
        self.setBackwardOutput(backwardOutput)
        
class LinearOutputLayer(OutputLayer):
    """ Output layer with a linear activation function. This layer can so far only be combined with an mse loss
    function."""
    
    def nonlinearity(self,linearActivation):
        """ Returns the nonlinear activation of the layer"""
        return linearActivation
    
    def computeBackwardOutput(self,target):
        """ Compute the backward output based on the derivative of the loss to the linear activation of this layer"""
        if not self.lossFunction == 'mse':
            raise NetworkError("a linear output layer can only be combined with a mse loss")
        if not isinstance(target,torch.Tensor):
            raise TypeError("Expecting a torch.Tensor object as target")
        if not self.forwardOutput.shape == target.shape:
            raise ValueError('Expecting a tensor of dimensions: batchdimension x class dimension x 1. Given target'
                             'has shape' + str(target.shape))
        backwardOutput = 2*(self.forwardOutput - target)
        self.setBackwardOutput(backwardOutput)
        

class Network(object):
    """ Network consisting of multiple layers. This class provides a range of methods to facilitate training of the
    networks """
    
    def __init__(self, layers):
        """
        :param layers: list of all the layers in the network
        """
        self.setLayers(layers)
        
    def setLayers(self,layers):
        if not isinstance(layers,list):
            raise TypeError("Expecting a list object containig all the layers of the network")
        if len(layers) < 2:
            raise ValueError("Expecting at least 2 layers (including input and output layer) in a network")
        if not isinstance(layers[0],InputLayer):
            raise TypeError("First layer of the network should be of type InputLayer")
        if not isinstance(layers[-1],OutputLayer):
            raise TypeError("Last layer of the network should be of type OutputLayer")
        for i in range(1,len(layers)):
            if not isinstance(layers[i],Layer):
                TypeError("All layers of the network should be of type Layer")
            if not layers[i-1].layerDim == layers[i].inDim:
                raise ValueError("layerDim should match with inDim of next layer")

        self.layers = layers


    
    












