# -*- coding: utf-8 -*-
from mozaik.analysis.analysis import *
from mozaik.analysis.helper_functions import psth


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





class SpikeCountCutout(Analysis):
    """
    For each recording in the datastore view it creates an AnalogSignalList containing the PSTH of the neuron
    using the bin length `required_parameters.bin_length`.

    Other parameters
    ------------------- 
    bin_length : float
             The bin length of the spike count

    """  
    required_parameters = ParameterSet({
        'bin_length': float,  # the bin length of the PSTH
        'start': float, 
        'end': float, 
    })

    def perform_analysis(self):
        # make sure spiketrains are also order in the same way
        print "SpikeCountCutout:", self.parameters.start, self.parameters.end
        for sheet in self.datastore.sheets():
            dsv = queries.param_filter_query(self.datastore,sheet_name=sheet)
            for st, seg in zip([MozaikParametrized.idd(s) for s in dsv.get_stimuli()],dsv.get_segments()):
                # segment cutout part
                for j,t in enumerate(seg.spiketrains):
                    seg.spiketrains[j] = t.time_slice( self.parameters.start*qt.ms, self.parameters.end*qt.ms )
                # stimuli cutout part
                st.duration = self.parameters.end-self.parameters.start

                psths = psth(seg.get_spiketrain(seg.get_stored_spike_train_ids()), self.parameters.bin_length, normalize=False)
                self.datastore.full_datastore.add_analysis_result(
                    AnalogSignalList(
                        psths,
                        seg.get_stored_spike_train_ids(),
                        psths[0].units,
                        x_axis_name='time',
                        y_axis_name='spike count (bin=' + str(self.parameters.bin_length) + ')',
                        sheet_name=sheet,
                        tags=self.tags,
                        analysis_algorithm=self.__class__.__name__,
                        stimulus_id=str(st)
                    )
                )
