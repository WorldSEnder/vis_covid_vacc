RESULT_SVGS := results/africa.svg\
               results/africa_partial.svg\
               results/asia.svg\
               results/asia_partial.svg\
               results/europe.svg\
               results/europe_partial.svg\
               results/middle_east.svg\
               results/middle_east_partial.svg\
               results/north_america.svg\
               results/north_america_partial.svg\
               results/oce.svg\
               results/oce_partial.svg\
               results/south_america.svg\
               results/south_america_partial.svg\
               results/usa.svg\
               results/usa_partial.svg\
               results/world.svg\
               results/world_partial.svg

RESULT_PNGS := $(RESULT_SVGS:.svg=.png)
SETUP_DEPS  := ./covid-19-data/.git\
               ./node_modules/.

$(RESULT_SVGS) &: $(SETUP_DEPS) draw_vis.py
	PYTHONHASHSEED=0 python ./draw_vis.py

%.png: %.svg $(SETUP_DEPS)
	npx svgexport $< $@ "svg{background:#f8f8ff;}"

all: $(SETUP_DEPS) $(RESULT_SVGS) $(RESULT_PNGS) ;

update: $(SETUP_DEPS)
	git submodule foreach --recursive git fetch --depth 1
	git submodule foreach --recursive git reset --hard FETCH_HEAD

./node_modules/.: package-lock.json
	npm ci

./covid-19-data/.git:
	git submodule update --init --recursive --depth 1

setup: $(SETUP_DEPS)
	python -m pip install -r requirements.txt

.DEFAULT_GOAL := all
.PHONY: all update setup
