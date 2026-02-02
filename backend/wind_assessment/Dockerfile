FROM continuumio/miniconda3

WORKDIR /app

RUN conda install -y -c conda-forge \
    flask \
    flask-cors \
    numpy \
    pandas \
    xarray \
    dask \
    netcdf4 \
    matplotlib \
    shapely \
    scipy \
    pyproj \
    cartopy \
    geopandas \
    rioxarray \
    zarr \
    && conda clean -afy

COPY . .

EXPOSE 4002

CMD ["python", "app.py"]
