FROM continuumio/miniconda3

WORKDIR /app

# Install dependencies from conda-forge to ensure compatibility (especially for cartopy/geopandas)
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
    && conda clean -afy

COPY . .

EXPOSE 4006

CMD ["python", "app.py"]
