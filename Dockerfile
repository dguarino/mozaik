#
# A Docker image for running mozaik simulations
#
# This image extends the "simulationx" image by adding mozaik dependencies
#
# Usage:
#
# docker build --no-chache -t mozaik .
# docker ps
# docker run -v `pwd`:`pwd` -w `pwd` -i -t mozaik /bin/bash


FROM neuralensemble/simulationx:py2

MAINTAINER domenico.guarino@cnrs.fr

##########################################################
# Xserver
CMD export DISPLAY=":0"


#######################################################
# Additional prerequisite libraries

RUN $VENV/bin/pip install imagen param cycler

RUN apt-get autoremove -y && \
    apt-get clean

#######################################################
WORKDIR $HOME
RUN git clone -b merged_JA_DG https://github.com/dguarino/mozaik.git
WORKDIR $HOME/mozaik
RUN python setup.py install

# Simple test:
# cd examples/VogelsAbbott2005
# python run.py nest 2 param/defaults 'test'
# mpirun -np 2 python run.py nest 2 param/defaults 'test'

#######################################################
# T2
WORKDIR $HOME
RUN git clone -b merged_JA_DG https://github.com/dguarino/T2.git

# testing
# python run_size_closed.py nest 8 param/defaults_mea 'data_size_closed_vsdi'
# python run_size_feedforward.py nest 8 param/defaults_mea 'data_size_feedforward_vsdi'
# python post_analyses.py