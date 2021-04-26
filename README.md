# A visualization of covid vaccination status

Does not use a nice visualization library, since the used
sunburst chart was not available. Instead, just dumps everything
into a svg.

<img alt="Sample result" src="https://raw.githubusercontent.com/WorldSEnder/vis_covid_vacc/artifacts/world.png" width="700" />

# Requirements

To run draw_vis.py, you need to have git installed, which is
required to automatically fetch the date of the data sources.

You also have to install the `svgexport` npm package. Other svg
to png converters I tried all failed to convert the `textPath` properly.

# Updating the data

Run `make update`. Updating the data is best done by shallowing updating
the covid-19-data, since otherwise you'd fetch a few gigabytes of history
(the repo is pretty large).

# Generating the visualization

Run `make all`.
