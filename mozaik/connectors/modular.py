# encoding: utf-8
import mozaik
import numpy
import ast
from mozaik.connectors import Connector
from mozaik.connectors.modular_connector_functions import ModularConnectorFunction
from collections import Counter
from parameters import ParameterSet, ParameterDist
from mozaik.tools.misc import sample_from_bin_distribution, normal_function
from mozaik import load_component


logger = mozaik.getMozaikLogger()

class ExpVisitor(ast.NodeVisitor):
    """
    AST tree visitor used for determining list of variables in the delay or weight expresions
    """
    
    def __init__(self,**params):
        ast.NodeVisitor.__init__(self,**params)
        self.names = []
    
    def visit_Name(self, node):
        node.id
        if not (node.id in self.names):
           self.names.append(node.id) 

class ModularConnector(Connector):
    """
    An abstract connector than allows for mixing of various factors that can affect the connectivity.
    
    The connector sepparates the implementation of delays from the implementation of weights.
    
    It receives a dictionary of weight functions and a dictonary of delays functions each being an instance of ModularConnectorFunction. 
    In both cases the list of functions is combined by using expression string which is a parameter of this class (see parameters for details). 
    
    The values returned by the ModularConnectorFunction will be considered to be in miliseconds when used for specifying delays, or the units used by pyNN for weights 
    in case of specifying weights.
    
    The ModularConnector then sets such computed values of weights and delays directly in the connections.
    
    
    """

    required_parameters = ParameterSet({
        'weight_functions' : ParameterSet, # a dictionary of ModularConnectorFunction's and their parameters that will be used to determine the weights.
                                           # strucutured as follows
                                           #            {
                                           #                 component : 'class_name_of_the_ModularConnectorFunction',
                                           #                 params : {
                                           #                           ...
                                           #                         }
                                           #             }
        'delay_functions' : ParameterSet, # the same as weight_functions but for delays
        'weight_expression' : str, # a python expression that can use variables f1..fn where n is the number of functions in weight_functions, and fi corresponds to the name given to a ModularConnectorFunction in weight_function ParameterSet. It determines how are the weight functions combined to obtain the weights
        'delay_expression' : str, # a python expression that can use variables f1..fn where n is the number of functions in delays_functions, and fi corresponds to the name given to a ModularConnectorFunction in delays_function ParameterSet. It determines how are the delays functions combined to obtain the delays
        'fan_in' : bool, # whether the ModularConnectionFunctions define distributions over pre- or post-synaptic neurons populations.
    })
    
    def __init__(self, network, name, source, target, parameters):
      Connector.__init__(self, network, name, source, target, parameters)
      if self.parameters.fan_in:
         self.fan_source = self.source
         self.fan_target = self.target
      else:
         self.fan_source = self.target
         self.fan_target = self.source

      # lets load up the weight ModularConnectorFunction's
      self.weight_functions = {}
      self.delay_functions = {}
      self.simulator_time_step = self.sim.get_time_step()
      # lets determine the list of variables in weight expressions
      v = ExpVisitor()
      v.visit(ast.parse(self.parameters.weight_expression))
      self.weight_function_names = v.names
      # lets determine the list of variables in delay expressions
      v = ExpVisitor()
      v.visit(ast.parse(self.parameters.delay_expression))
      self.delay_function_names = v.names
      
      for k in self.weight_function_names:
          self.weight_functions[k] = load_component(self.parameters.weight_functions[k].component)(self.fan_source,self.fan_target,self.parameters.weight_functions[k].params)
          assert isinstance(self.weight_functions[k],ModularConnectorFunction)
          
      for k in self.delay_function_names:
          self.delay_functions[k] = load_component(self.parameters.delay_functions[k].component)(self.fan_source,self.fan_target,self.parameters.delay_functions[k].params)
    
    def _obtain_weights(self,i):
        """
        This function calculates the combined weights from the ModularConnectorFunction in weight_functions
        """
        evaled = {}
       
        for k in self.weight_function_names:
            evaled[k] = self.weight_functions[k].evaluate(i)
        return numpy.zeros((self.fan_source.pop.size,)) + eval(self.parameters.weight_expression,globals(),evaled)
        
    def _obtain_delays(self,i):
        """
        This function calculates the combined weights from the ModularConnectorFunction in weight_functions
        """
        evaled = {}
        for k in self.delay_function_names:
            evaled[k] = self.delay_functions[k].evaluate(i)
        
        delays = numpy.zeros((self.fan_source.pop.size,)) + eval(self.parameters.delay_expression,globals(),evaled)
        #round to simulation step            
        delays = numpy.rint(delays / self.simulator_time_step) * self.simulator_time_step
        return delays
    
    def _determine_weights_and_delays(self,i):    
        """
        This returns three lists of equal length, first corresponding to indices of the connections in fan_source population corresponding to the
        fan_target neuron i, and the last two are corresponding weights and delays.
        """
        return numpy.arange(0,self.fan_source.pop.size,1), self.weight_scaler*self._obtain_weights(i).flatten(), self._obtain_delays(i).flatten()

    def _connect(self):
        fan_source_indexes = []
        fan_target_indexes = []
        weights = []    
        delays = []
        for i in numpy.nonzero(self.fan_target.pop._mask_local)[0]: 
            _fan_source_indexes, _weights, _delays = self._determine_weights_and_delays(i)
            fan_source_indexes.extend(_fan_source_indexes)
            fan_target_indexes.extend(numpy.zeros((len(_fan_source_indexes),))+i)
            weights.extend(_weights)
            delays.extend(_delays)

        if self.parameters.fan_in:
            connections_list = zip(fan_source_indexes, fan_target_indexes, weights, delays)
        else:
            connections_list = zip(fan_target_indexes, fan_source_indexes, weights, delays)

        self.method = self.sim.FromListConnector(connections_list)
        if len(connections_list) > 0:
            self.proj = self.sim.Projection(
                                self.source.pop,
                                self.target.pop,
                                self.method,
                                synapse_type=self.init_synaptic_mechanisms(),
                                label=self.name,
                                receptor_type=self.parameters.target_synapses)
        else:
            logger.warning("%s(%s): empty projection - pyNN projection not created." % (self.name,self.__class__.__name__))

class ModularSamplingProbabilisticConnector(ModularConnector):
    """
    ModularConnector that interprets the weights as proportional probabilities of connectivity
    and for each neuron in connections it samples num_samples of
    connections that actually get realized according to these weights.
    Each such sample connections will have weight equal to
    base_weight but note that there can be multiple
    connections between a pair of neurons in this sample (in which case the
    weights are set to the multiple of the base weights times the number of
    occurrences in the sample).
    """

    required_parameters = ParameterSet({
        'num_samples': ParameterDist,
        'base_weight' : ParameterDist
    })

    def _determine_weights_and_delays(self,i):    
        weights = self._obtain_weights(i)
        delays = self._obtain_delays(i)
        co = Counter(sample_from_bin_distribution(weights, self.parameters.num_samples.next()))
        return co.keys(),[self.weight_scaler*self.parameters.base_weight.next()*co[k] for k in co.keys()],[delays[k] for k in co.keys()]


class ModularSingleWeightProbabilisticConnector(ModularConnector):
    """
    ModularConnector that interprets the weights as proportional probabilities of connectivity.
    The parameter connection_probability is interepreted as the average probability that two neurons will be connected in this 
    projection. For each pair this connecter will make one random choice of connecting them (where the probability of this choice
    is determined as the proportional probability of the corresponding weight normalized by the connection_probability parameter).
    It will set each connections to the weight base_weight.
    """

    required_parameters = ParameterSet({
        'connection_probability': float,
        'base_weight' : ParameterDist
    })

    def _determine_weights_and_delays(self,i):
        weights = self._obtain_weights(i)
        delays = self._obtain_delays(i)
        conections_probabilities = weights/numpy.sum(weights)*self.parameters.connection_probability*len(weights)
        connection_indices = numpy.flatnonzero(conections_probabilities > numpy.random.rand(len(conections_probabilities)))
        return connection_indices,[self.weight_scaler*self.parameters.base_weight.next() for k in connection_indices],[delays[k] for k in connection_indices]


        
