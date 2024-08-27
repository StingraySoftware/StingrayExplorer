FROM python:3.11.9

WORKDIR /code

COPY . .

RUN python3 -m pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir astropy
RUN pip install --no-cache-dir scipy
RUN pip install --no-cache-dir matplotlib
RUN pip install --no-cache-dir numpy
RUN pip install --no-cache-dir tqdm
RUN pip install --no-cache-dir numba
RUN pip install --no-cache-dir pint-pulsar
RUN pip install --no-cache-dir emcee
RUN pip install --no-cache-dir corner
RUN pip install --no-cache-dir statsmodels
RUN pip install --no-cache-dir stingray
RUN pip install --no-cache-dir panel
RUN pip install --no-cache-dir watchfiles
RUN pip install --no-cache-dir holoviews
RUN pip install --no-cache-dir hvplot
RUN pip install --no-cache-dir param
RUN pip install --no-cache-dir pandas


CMD ["panel", "serve", "explorer.py", "--autoreload", "--static-dirs", "assets=./assets", "--address", "0.0.0.0", "--port", "7860", "--allow-websocket-origin", "*"]

