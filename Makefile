RESULT_SVGS := results/africa.svg\
               results/asia.svg\
               results/europe.svg\
               results/middle_east.svg\
               results/north_america.svg\
               results/oce.svg\
               results/south_america.svg\
               results/usa.svg\
               results/world.svg
RESULT_PNGS := $(RESULT_SVGS:.svg=.png)
SETUP_DEPS  := ./covid-19-data/.git\
               ./node_modules/.

$(RESULT_SVGS) &: $(SETUP_DEPS) draw_vis.py
	python ./draw_vis.py

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
