from mozaik.core import ParametrizedObject
from mozaik.tools.circ_stat import circular_dist
from parameters import ParameterSet
import math
import numpy
import mozaik
from mozaik.sheets.population_selector import PopulationSelector


class SimilarAnnotationGrid(PopulationSelector):
      """
      This PopulationSelector picks a grid of neurons whose *annotation* value is closer than *distance* from specified *value* (based on euclidian norm).
      
      Other parameters
      ----------------
      annotation : str
                 The name of the annotation value. It has to be defined in the given population for all neurons.
      
      distance : The the upper limit on distance between the given neurons annotation value and the specified value that permits inclusion.
      
      value : The value from which to calculate distance.
      
      size : float (micro meters of cortical space)
           The size of the grid (it is assumed to be square) - it has to be multiple of spacing 
      
      spacing : float (micro meters of cortical space)
           The space between two neighboring electrodes.

      offset_x : float (micro meters of cortical space)
           The x axis offset from the center of the sheet.

      offset_y : float (micro meters of cortical space)
           The y axis offset from the center of the sheet.
      """
      
      required_parameters = ParameterSet({
        'annotation' : str,
        'distance' : float,
        'value': float,
        'period' :  float, # if the value is periodic this should be set to the period, oterwise it should be set to 0.
        'size': float,  # the size of the grid (it is assumed to be square) - it has to be multiple of spacing (micro meters)
        'spacing' : float, #the space between two electrodes (micro meters)
        'offset_x' : float, # the x axis offset from the center of the sheet (micro meters)
        'offset_y' : float, # the y axis offset from the center of the sheet (micro meters)
      })  

      
      def generate_idd_list_of_neurons(self):
          grid_ids = []
          picked = []
          assert math.fmod(self.parameters.size,self.parameters.spacing) < 0.000000001 , "Error the size has to be multiple of spacing!"

          z = self.sheet.pop.all_cells.astype(int)

          for x in self.parameters.offset_x + numpy.arange(0,self.parameters.size,self.parameters.spacing) - self.parameters.size/2.0:
              for y in self.parameters.offset_y + numpy.arange(0,self.parameters.size,self.parameters.spacing) - self.parameters.size/2.0:
                  xx,yy = self.sheet.cs_2_vf(x,y)
                  grid_ids.append(numpy.argmin(numpy.power(self.sheet.pop.positions[0] - xx,2) +  numpy.power(self.sheet.pop.positions[1] - yy,2)))
          
          g = list(set(grid_ids))

          vals = [self.sheet.get_neuron_annotation(idx, self.parameters.annotation) for idx in g]

          if self.parameters.period != 0:
            picked = numpy.array([i for i in xrange(0,len(g)) if abs(vals[i]-self.parameters.value) < self.parameters.distance])
          else:
            picked = numpy.array([i for i in xrange(0,len(g)) if circular_dist(vals[i],self.parameters.value,self.parameters.period) < self.parameters.distance])  
         
          return z[picked[:]]

