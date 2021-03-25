RESULT_SVGS := result_africa.svg\
               result_asia.svg\
			   result_europe.svg\
			   result_middle_east.svg\
			   result_north_america.svg\
			   result_oce.svg\
			   result_south_america.svg\
			   result_usa.svg\
			   result_world.svg
RESULT_PNGS := $(RESULT_SVGS:.svg=.png)

$(RESULT_SVGS) &: setup ./covid-19-data/.git draw_vis.py
	python ./draw_vis.py

%.png: %.svg setup
	npx svgexport $< $@ "svg{background:#f8f8ff;}"

all: setup $(RESULT_SVGS) $(RESULT_PNGS) ;

update: setup
	git submodule foreach --recursive git fetch --depth 1
	git submodule foreach --recursive git reset --hard FETCH_HEAD

./node_modules/.: package-lock.json
	npm ci

./covid-19-data/.git:
	git submodule update --init --recursive --depth 1

setup: ./covid-19-data/.git ./node_modules/. ;

.DEFAULT_GOAL := all
.PHONY: all update setup
