docker build --no-cache -t mozaik .
docker run -v `pwd`:`pwd` -w `pwd` -i -t mozaik /bin/bash
