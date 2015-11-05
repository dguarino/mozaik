# -*- coding: utf-8 -*-
from mozaik.analysis.analysis import *

class TrialAveragedFiringRateCutout(TrialAveragedFiringRate):


    def analyse(self, start=None, end=None):
        """
        This is the function calls to perform the analysis.
        """
        t1 = time.time()
        logger.info('Starting ' + self.__class__.__name__ + ' analysis')
        self.perform_analysis( start, end )
        t2 = time.time()
        logger.warning(self.__class__.__name__ + ' analysis took: ' + str(t2-t1) + 'seconds')


    def perform_analysis(self, start=None, end=None):
        for sheet in self.datastore.sheets():
            dsv1 = queries.param_filter_query(self.datastore, sheet_name=sheet)
            segs = dsv1.get_segments() # from datastore DataStoreView
            # new part
            # print segs[0].spiketrains[0]
            for i,s in enumerate(segs):
                for j,t in enumerate(s.spiketrains):
                    segs[i].spiketrains[j] = t.time_slice( start*qt.ms, end*qt.ms )
            # print segs[0].spiketrains[0]

            st = [ MozaikParametrized.idd(s) for s in dsv1.get_stimuli() ]
            # print "st:", st
            for i,s in enumerate(st):
                st[i].duration = end-start
            # print "st:", st

            # transform spike trains due to stimuly to mean_rates
            mean_rates = [numpy.array(s.mean_rates()) for s in segs]
            
            # join rates and stimuli
            (mean_rates, s) = colapse(mean_rates, st, parameter_list=['trial'])
            # take a sum of each
            mean_rates = [sum(a)/len(a) for a in mean_rates]

            #JAHACK make sure that mean_rates() return spikes per second
            units = munits.spike / qt.s
            logger.debug('Adding PerNeuronValue containing trial averaged firing rates to datastore')
            for mr, st in zip(mean_rates, s):
                self.datastore.full_datastore.add_analysis_result(
                    PerNeuronValue(
                        mr,
                        segs[0].get_stored_spike_train_ids(),
                        units,
                        stimulus_id=str(st),
                        value_name='Firing rate',
                        sheet_name=sheet,
                        tags=self.tags,
                        analysis_algorithm=self.__class__.__name__,
                        period=None
                    )
                )

