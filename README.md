# A visualization of covid vaccination status

Does not us a nice visualization library, since the used
sunburst chart was not available. Instead, just dumps everything
into a svg.

# Requirements

To run draw_vis.py, you need to have git installed, which is
required to automatically fetch the date of the data sources.

# Updating the data and result

Run 'python ./draw_vis.py'. Updating the data is best done
by shallowing updating the covid-19-data, since otherwise
you'd fetch a few gigabytes of history (the repo is pretty large).

