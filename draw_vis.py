"""Draw covid vaccination data as svg
"""
import os
import csv
import glob
import json
import textwrap
from collections import defaultdict
from itertools import cycle
from math import asin, cos, pi, sin, sqrt

from lxml import etree as ET

# Inner radius for per country display
COUNTRY_SPEC_INNER = 200
# Width of country specific segments segments
COUNTRY_SPEC_WIDTH = 200
# Width of spacing between each entry
SPACING_SIZE = 1
ACCEPTABLE_SIZE = 10
STROKES = 2
STROKE_COLOR = "#aaa"

def rotate_to_view(phi):
    # convert into "view coordinates", where 0 is up
    return - 1 / 2 * pi + phi

def sector(radius_min=0, radius_max=1, phi_start=0, phi_end=pi/2):
    spacing_inner = asin((SPACING_SIZE / 2) / radius_min)
    spacing_outer = asin((SPACING_SIZE / 2) / radius_max)
    phi_start = rotate_to_view(phi_start)
    phi_end = rotate_to_view(phi_end)

    start_inner_x = radius_min * cos(phi_start + spacing_inner)
    start_inner_y = radius_min * sin(phi_start + spacing_inner)
    start_outer_x = radius_max * cos(phi_start + spacing_outer)
    start_outer_y = radius_max * sin(phi_start + spacing_outer)
    end_inner_x = radius_min * cos(phi_end - spacing_inner)
    end_inner_y = radius_min * sin(phi_end - spacing_inner)
    end_outer_x = radius_max * cos(phi_end - spacing_outer)
    end_outer_y = radius_max * sin(phi_end - spacing_outer)

    large = 1 if abs(phi_end - phi_start) > pi else 0
    counterclock = 1 if phi_end > phi_start else 0

    return ET.Element("path", attrib={
        "d": textwrap.dedent(f"""
                M{start_inner_x} {start_inner_y}
                L{start_outer_x} {start_outer_y}
                A{radius_max} {radius_max} 0 {large} {counterclock} {end_outer_x} {end_outer_y}
                L{end_inner_x} {end_inner_y}
                A{radius_min} {radius_min} 0 {large} {1 - counterclock} {start_inner_x} {start_inner_y}
              """).replace("\n", "")
    })

def circle_part(radius=0, phi_start=0, phi_end=pi/2):
    phi_start = rotate_to_view(phi_start)
    phi_end = rotate_to_view(phi_end)
    # add half of stroke width
    radius += STROKES / 2

    start_x = radius * cos(phi_start)
    start_y = radius * sin(phi_start)
    end_x = radius * cos(phi_end)
    end_y = radius * sin(phi_end)

    large = 1 if abs(phi_end - phi_start) > pi else 0
    counterclock = 1 if phi_end > phi_start else 0

    return ET.Element("path", attrib={
        "d": textwrap.dedent(f"""
                M{start_x} {start_y}
                A{radius} {radius} 0 {large} {counterclock} {end_x} {end_y}
              """).replace("\n", ""),
        "stroke": STROKE_COLOR,
        "stroke-width": f"{STROKES}",
        "fill": "none",
    })

def seperator(radius_inner, radius_outer, phi):
    phi = rotate_to_view(phi)
    start_inner_x = radius_inner * cos(phi)
    start_inner_y = radius_inner * sin(phi)
    start_outer_x = radius_outer * cos(phi)
    start_outer_y = radius_outer * sin(phi)

    return ET.Element("path", attrib={
        "d": textwrap.dedent(f"""
                M{start_inner_x} {start_inner_y}
                L{start_outer_x} {start_outer_y}
              """).replace("\n", ""),
        "stroke": STROKE_COLOR,
        "stroke-width": f"{STROKES}",
        "fill": "none",
    })

def model_people_vacc(country):
    if country is None:
        return None
    country_data = country["data"]
    # just use latest available data
    # latest available data point for fully vaccinated population
    latest_with_full_pop = ([
        d for d in country_data if "people_fully_vaccinated" in d
    ] or [None])[-1]
    # latest available data point for initially vaccinated population
    latest_with_vacc = ([
        d for d in country_data if "people_vaccinated" in d
    ] or [None])[-1]
    # latest available data points for vaccination shots
    latest_with_shots = ([
        d for d in country_data if "total_vaccinations" in d
    ] or [None])[-1]

    if latest_with_full_pop is not None:
        return latest_with_full_pop["people_fully_vaccinated"]
    if latest_with_vacc is not None:
        # positively biased assumption
        # maybe display with another pattern?
        return latest_with_vacc["people_vaccinated"]
    if latest_with_shots is not None:
        # divide by two to get a conservative number ...
        return latest_with_shots["total_vaccinations"] / 2
    return None

def model_people_vacc_partial(country):
    if country is None:
        return None
    country_data = country["data"]
    # just use latest available data
    # latest available data point for fully vaccinated population
    latest_with_full_pop = ([
        d for d in country_data if "people_fully_vaccinated" in d
    ] or [None])[-1]
    # latest available data point for initially vaccinated population
    latest_with_vacc = ([
        d for d in country_data if "people_vaccinated" in d
    ] or [None])[-1]
    # latest available data points for vaccination shots
    latest_with_shots = ([
        d for d in country_data if "total_vaccinations" in d
    ] or [None])[-1]

    if latest_with_vacc is not None:
        # positively biased assumption
        # maybe display with another pattern?
        return latest_with_vacc["people_vaccinated"]
    if latest_with_full_pop is not None:
        return latest_with_full_pop["people_fully_vaccinated"]
    if latest_with_shots is not None:
        # divide by two to get a conservative number ...
        return latest_with_shots["total_vaccinations"] / 2
    return None

def model_people_vacc_state(state_data):
    return int(state_data["Series_Complete_Yes"])

def model_people_vacc_state_partial(state_data):
    return int(float(state_data["Administered_Dose1_Recip"]))

def xmlescape(data):
    """format usage in format strings only!!!"""
    from xml.sax.saxutils import escape
    return escape(data, entities={
        "'": "&apos;",
        "\"": "&quot;"
    })

class Datapoint():
    @property
    def hash(self):
        raise NotImplementedError()
    @property
    def label(self):
        raise NotImplementedError()
    @property
    def size(self):
        raise NotImplementedError()
    @property
    def fraction_filled(self):
        raise NotImplementedError()
    @property
    def children(self):
        raise NotImplementedError()

class Country(Datapoint):
    def __init__(self, pop_data, vacc_data):
        self._pop_data = pop_data
        self._vacc_data = vacc_data

    @property
    def label(self):
        return self._pop_data["country"]

    @property
    def hash(self):
        return hash(self._pop_data["iso_code"])

    @property
    def size(self):
        return self._pop_data["population"]

    @property
    def model_count(self):
        return model_people_vacc(self._vacc_data)

    @property
    def fraction_filled(self):
        people_vacced = self.model_count
        if people_vacced is not None:
            return people_vacced / self.size
        return None

    @property
    def children(self):
        return []

class CountryPartial(Country):
    @property
    def model_count(self):
        return model_people_vacc_partial(self._vacc_data)

class USState(Datapoint):
    def __init__(self, state_data):
        self._sdata = state_data

    @property
    def label(self):
        return self._sdata["LongName"]

    @property
    def hash(self):
        return self._sdata["ShortName"]

    @property
    def size(self):
        return int(float(self._sdata["Census2019"]))

    @property
    def model_count(self):
        return model_people_vacc_state(self._sdata)

    @property
    def fraction_filled(self):
        people_vacced = self.model_count
        return people_vacced / self.size

    @property
    def children(self):
        return []

class USStatePartial(USState):
    @property
    def model_count(self):
        return model_people_vacc_state_partial(self._sdata)

class Region(Datapoint):
    def __init__(self, region, subregions):
        self._region = region
        self._subregions = subregions

    @property
    def label(self):
        return self._region

    @property
    def hash(self):
        return hash(self._region)

    @property
    def size(self):
        return sum(s.size for s in self._subregions)

    @property
    def fraction_filled(self):
        if all(s.fraction_filled is None for s in self._subregions):
            return None
        people_vacced = sum(
            s.fraction_filled * s.size for s in self._subregions
            if s.fraction_filled is not None
        )
        size_with_data = sum(
            s.size for s in self._subregions
            if s.fraction_filled is not None
        )
        return people_vacced / size_with_data

    @property
    def children(self):
        return self._subregions

class FakeClass(Datapoint):
    def __init__(self, standins):
        self._standins = sorted(
            standins,
            key=lambda s: (0 if s.fraction_filled is None else s.fraction_filled * s.size, s.size),
            reverse=True,
        )

    @property
    def label(self):
        if not self._standins:
            return ""
        if len(self._standins) == 1:
            return self._standins[0].label
        (s1, s2, *rest) = self._standins
        if rest:
            return ", ".join((s1.label, s2.label, "etc."))
        return f"{s1.label} & {s2.label}"

    @property
    def hash(self):
        return hash(tuple(s.hash for s in self._standins))

    @property
    def size(self):
        return sum(s.size for s in self._standins)

    @property
    def fraction_filled(self):
        if all(s.fraction_filled is None for s in self._standins):
            return None
        people_vacced = sum(
            s.fraction_filled * s.size for s in self._standins
            if s.fraction_filled is not None
        )
        size_with_data = sum(
            s.size for s in self._standins
            if s.fraction_filled is not None
        )
        return people_vacced / size_with_data

    @property
    def children(self):
        def children_it():
            for s in self._standins:
                for c in s.children:
                    yield c
        return list(children_it())

# https://gist.github.com/xgfs/37436865b6616eebd09146007fea6c09
PALETTE_XGFS_NORMAL12 = cycle(
    [(235, 172, 35), (184, 0, 88), (0, 140, 249), (0, 110, 0), (0, 187, 173), (209, 99, 230), (178, 69, 2), (255, 146, 135), (89, 84, 214), (0, 198, 248), (135, 133, 0), (0, 167, 108), (189, 189, 189)]
)

def bunch_datapoints(datapoints, inner_radius, radian_size):
    """
    Create a new 'Other' datapoint such that the spacing
    is at most 1/5th of one datapoint.
    """
    spacing_radians = asin(SPACING_SIZE / inner_radius)
    datapoints = sorted(
        datapoints,
        key=lambda d: d.size,
        reverse=True,
    )
    data_size = sum(d.size for d in datapoints)
    def calc_radian_per_size(datacount):
        # Only need padding between items. If the whole circle
        # the padding between start and end also counts.
        padding_count = datacount - 1 if radian_size < 2 * pi else datacount
        # radian_size = data_size * rads_per_size + SPACING_RADIANS * padding_count
        rads_per_size = (radian_size - spacing_radians * padding_count) / data_size
        return rads_per_size

    # now do a binary search for a good spacing
    cut = 0
    size_adjust = running_max_size = len(datapoints)
    # invariant: running_max_size - (cut + size_adjust) < size_adjust
    while size_adjust > 0:
        datacount = cut + size_adjust
        if datacount < len(datapoints):
            # include the 'Other' datapoint!
            datacount += 1
        rads_per_size = calc_radian_per_size(datacount)
        # spacing_size might be negative, if too many datapoints
        if rads_per_size > 0:
            # would be acceptable
            cut += size_adjust
            size_adjust = running_max_size - cut
        else:
            # not acceptable
            running_max_size = cut + size_adjust
            size_adjust = size_adjust // 2

    if not datapoints[cut:]:
        return datapoints
    potential_fake = FakeClass(datapoints[cut:])
    rads_per_size = calc_radian_per_size(cut)
    if potential_fake.size * rads_per_size * inner_radius > ACCEPTABLE_SIZE:
        return datapoints[0:cut] + [potential_fake]
    # bunching all smaller data isn't enough, but surely
    # including one more element from datapoints will be
    cut -= 1
    actual_fakes = FakeClass(datapoints[cut:])
    return datapoints[0:cut] + [actual_fakes]

def draw_datapoints(svg, datapoints):
    datagroup = ET.Element("g")
    labelgroup = ET.Element("g")
    datapoints = bunch_datapoints(datapoints, COUNTRY_SPEC_INNER, 2 * pi)
    total_size = sum(d.size for d in datapoints)
    rads_per_size = 2 * pi / total_size

    total_ratio = FakeClass(datapoints).fraction_filled
    total_radius = sqrt(total_ratio) * (COUNTRY_SPEC_INNER - STROKES)
    section_all = ET.Element("circle", attrib={
        "fill": "#279ee3",
        "r": f"{total_radius}",
    })
    datagroup.append(section_all)

    radius_width = COUNTRY_SPEC_WIDTH
    def make_section(radian_start, dp, fill_color, radius_inner):
        radian_size = dp.size * rads_per_size
        radian_end = radian_start + radian_size

        d_ratio = dp.fraction_filled
        if d_ratio is None: # no data
            outer_radius = radius_inner + radius_width
            section_d = sector(radius_inner, outer_radius, radian_start, radian_end)
            section_d.attrib["fill"] = "url(#diagonalHatch)"
            datagroup.append(section_d)
        else:
            # don't use d_ratio directly, be correct about visual area
            # radius_ratio^2 = ratio * radius_outer^2 + (1-ratio) * radius_inner^2
            radius_ratio = sqrt(d_ratio * (radius_inner + radius_width) ** 2 + (1 - d_ratio) * radius_inner ** 2)
            section_d = sector(radius_inner, radius_ratio, radian_start, radian_end)
            r, g, b = fill_color
            section_d.attrib["fill"] = f"#{r:02x}{g:02x}{b:02x}"
            datagroup.append(section_d)

        outer_circle = circle_part(radius_inner + radius_width, radian_start, radian_end)
        svg.append(outer_circle)

        if radian_size * radius_inner > 4:
            small_label_size = int(radian_size * radius_inner)
            label_outside_in = radian_start + radian_size / 2 > pi
            overflow = COUNTRY_SPEC_INNER / 2
            (label_r_start, label_r_end) = (radius_inner - overflow, radius_inner + radius_width + overflow)
            if label_outside_in:
                (label_r_start, label_r_end) = (label_r_end, label_r_start)
            label_path = seperator(
                label_r_start, label_r_end, radian_start + radian_size / 2
            )
            label_id = f"textpath-{dp.hash}"
            label_path.attrib["id"] = label_id
            label_defs = ET.Element("defs")
            label_defs.append(label_path)
            label_text = ET.Element("text", attrib={
                "text-anchor": "middle",
                "dominant-baseline": "middle",
                "class": f"small-label-{small_label_size}" if small_label_size < 10 else "label",
            })
            label_textpath = ET.Element("textPath", attrib={
                "href": f"#{label_id}",
                "startOffset": "50%",
            })
            if d_ratio is None:
                fmt_per = "(n/a)"
            else:
                fmt_per = f"{100 * d_ratio:.1f}%"
            label_content = ET.fromstring(Rf"""
            <tspan>{xmlescape(dp.label)} | {fmt_per}</tspan>
            """
            )
            label_textpath.append(label_content)
            label_text.append(label_textpath)
            labelgroup.append(label_defs)
            labelgroup.append(label_text)

        radius_children = radius_inner + radius_width + STROKES
        children = bunch_datapoints(dp.children, radius_children, radian_size)
        if len(children) <= 1:
            return False
        radian_start_child = radian_start
        for d_child, d_color in zip(children, PALETTE_XGFS_NORMAL12):
            make_section(radian_start_child, d_child, d_color, radius_children)
            radian_start_child += d_child.size * rads_per_size
        return True
    # start with half a padding
    radian_done = 0.0
    for dp, dcolor in zip(datapoints, PALETTE_XGFS_NORMAL12):
        is_nested = make_section(radian_done, dp, dcolor, COUNTRY_SPEC_INNER)
        sep_before = seperator(
            COUNTRY_SPEC_INNER,
            COUNTRY_SPEC_INNER + COUNTRY_SPEC_WIDTH,
            radian_done
        )
        radian_done += dp.size * rads_per_size
        sep_after = seperator(
            COUNTRY_SPEC_INNER,
            COUNTRY_SPEC_INNER + COUNTRY_SPEC_WIDTH,
            radian_done
        )
        if is_nested:
            svg.append(sep_before)
            svg.append(sep_after)
    svg.append(datagroup)
    svg.append(labelgroup)

def get_date_of_data():
    import subprocess
    git_date = subprocess.run(
        ["git", "log", "-1", "--format=%cd"],
        cwd="./covid-19-data/",
        check=True,
        capture_output=True
    )
    return git_date.stdout.decode('utf-8').strip()

class ModelFull():
    def __init__(self, criteria_label, label_all, basename):
        self.criteria_label = criteria_label
        self.label_all = label_all
        self.filename = f"results/{basename}.svg"

    def legend(self, dimension):
        return ET.fromstring(Rf'''
            <text y="{dimension}" class="legend">
            <tspan x="-{dimension}">* Showing percentage of population fully vaccinated, having received all shots according to each countries chosen vaccine(s).</tspan>
            <tspan x="-{dimension}" dy="1.2em">Countries where no data was available are not counted towards a region's percentage.</tspan>
            </text>
            '''
        )

    def title(self, dimension):
        return ET.fromstring(Rf'''
            <text y="{-dimension}" class="title" text-anchor="middle">
                <tspan x="0">Covid Vaccinations* by {self.criteria_label}</tspan>
            </text>
            '''
        )

    @property
    def timestamp(self):
        return get_date_of_data()

class ModelPartial():
    def __init__(self, criteria_label, label_all, basename):
        self.criteria_label = criteria_label
        self.label_all = label_all
        self.filename = f"results/{basename}_partial.svg"

    def legend(self, dimension):
        return ET.fromstring(Rf'''
            <text y="{dimension}" class="legend">
            <tspan x="-{dimension}">* Showing percentage of population vaccinated, having received at least one shot of a countries chosen vaccine(s).</tspan>
            <tspan x="-{dimension}" dy="1.2em">Countries where no data was available are not counted towards a region's percentage.</tspan>
            </text>
            '''
        )

    def title(self, dimension):
        return ET.fromstring(Rf'''
            <text y="{-dimension}" class="title" text-anchor="middle">
            <tspan x="0">Partial Covid Vaccinations* by {self.criteria_label}</tspan>
            </text>
            '''
        )

    @property
    def timestamp(self):
        return get_date_of_data()

def draw_diagram(model, datapoints):
    svg = ET.Element("svg", attrib={
        "xmlns": "http://www.w3.org/2000/svg",
    })
    style = ET.fromstring(
R'''
<style>
text {
    font-family: "Open Sans";
}
.legend, .sources {
    font-size: 10pt;
}
.title {
    font-size: 20pt;
    font-weight: bold;
}
.label_all {
    font-size: 18pt;
}
.label {
}
.small-label-9 {
   font-size: 9pt;
}
.small-label-8 {
   font-size: 8pt;
}
.small-label-7 {
   font-size: 7pt;
}
.small-label-6 {
   font-size: 6pt;
}
.small-label-5 {
   font-size: 5pt;
}
.small-label-4 {
   font-size: 4pt;
}
a {
    text-decoration: underline;
}
</style>
'''
    )
    svg.append(style)
    font_tag = ET.fromstring(
R'''
<style type='text/css'>
<![CDATA[@font-face{
  font-family:'Open Sans';src:local('Open Sans')
             , local('OpenSans')
             , url(https://fonts.gstatic.com/s/opensans/v18/mem5YaGs126MiZpBA-UN_r8OUuhp.woff2) format('woff2');
  }]]>
</style>
'''
    )
    svg.append(font_tag)
    hatch_pattern = ET.fromstring(
R"""
<pattern id="diagonalHatch" width="10" height="10" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
  <line x1="0" y1="0" x2="0" y2="10" style="stroke:#444; stroke-width:1" />
</pattern>
"""
    )
    defs = ET.Element("defs")
    defs.append(hatch_pattern)
    svg.append(defs)

    inner_circle = ET.Element("circle", attrib={
        "cx": "0",
        "cy": "0",
        "r": f"{COUNTRY_SPEC_INNER - STROKES/2}",
        "stroke": STROKE_COLOR,
        "stroke-width": f"{STROKES}",
        "fill": "none",
    })
    svg.append(inner_circle)
    draw_datapoints(svg, datapoints)

    dimension = 2 * COUNTRY_SPEC_WIDTH + COUNTRY_SPEC_INNER + 2 * STROKES + 50
    dimdim = 2 * dimension

    svg.append(model.legend(dimension))
    svg.append(model.title(dimension))
    sources = ET.fromstring(Rf'''
<text y="{dimension}" class="sources" text-anchor="end" xmlns:xlink="http://www.w3.org/1999/xlink">
    <tspan x="{dimension}">Data source:
        <a xlink:href="https://github.com/owid/covid-19-data/tree/master/public/data/vaccinations">
            <tspan>https://github.com/owid/covid-19-data/tree/master/public/data/vaccinations</tspan>
        </a>
    </tspan>
    <tspan x="{dimension}" dy="1.2em">Code source:
        <a xlink:href="https://github.com/WorldSEnder/vis_covid_vacc">
            <tspan>https://github.com/WorldSEnder/vis_covid_vacc</tspan>
        </a>
    </tspan>
    <tspan x="{dimension}" dy="1.2em">Timestamp: {model.timestamp}</tspan>
</text>
    ''')
    svg.append(sources)

    global_perc = FakeClass(datapoints).fraction_filled
    center_text = ET.fromstring(Rf'''
<text text-anchor="middle" dominant-baseline="middle" class="label_all" x="0" y="0">
    <tspan>{xmlescape(model.label_all)} | {100 * global_perc:.1f}%</tspan>
</text>
''')
    svg.append(center_text)

    svg.attrib["viewBox"] = f"-{dimension + 10} -{dimension + 30} {dimdim + 20} {dimdim + 80}"

    with open(model.filename, "wb") as result_h:
        result_h.write(ET.tostring(svg))

COUNTRIES_MIDDLE_EAST = (
      "EGY", "TUR", "IRN", "IRQ", "SAU"
    , "YEM", "SYR", "JOR", "ARE", "ISR"
    , "LBN", "PSE", "OMN", "KWT", "QAT"
    , "BHR")

MIDDLE_EAST_CONT = {
    "": "Middle East"
}

def main():
    with open("covid-19-data/public/data/vaccinations/vaccinations.json") as data_h:
        vacc_reader = json.load(data_h)
        vacc_data = {
            d["iso_code"]: d for d in vacc_reader
        }

    latest_cdc_data = max(glob.glob("covid-19-data/scripts/input/cdc/vaccinations/cdc_data_*"))
    print(f"Using cdc file {latest_cdc_data}")
    with open(latest_cdc_data) as states_data_h:
        vacc_usa_reader = csv.DictReader(states_data_h)
        vacc_usa_data = {
            d["LongName"]: d for d in vacc_usa_reader
            if d["Location"] not in ("US", "LTC", "VA2", "BP2", "DD2", "IH2")
        }

    with open("covid-19-data/scripts/input/owid/continents.csv", "r") as continents_h:
        region_reader = csv.DictReader(continents_h)
        country_to_continent = {
            c["Code"]: (c if c["Code"] not in COUNTRIES_MIDDLE_EAST else MIDDLE_EAST_CONT)
            for c in region_reader
        }

    with open("covid-19-data/scripts/input/un/population_2020.csv", "r") as pop_h:
        census_reader = csv.DictReader(pop_h)
        pop_data = [
            {
                "country": c["entity"],
                "iso_code": c["iso_code"],
                "population": int(c["population"])
            } for c in census_reader
            # census includes regions, filter those
            if len(c["iso_code"]) == 3
        ]
    # country list
    countries = pop_data
    # countries by continent
    continents = defaultdict(list)
    for ctry in countries:
        region = country_to_continent[ctry["iso_code"]]
        continents[region[""]].append(ctry)

    os.makedirs("results", exist_ok=True)

    for (Model, CountryDP, USStateDP) in [
            (ModelFull, Country, USState),
            (ModelPartial, CountryPartial, USStatePartial)
        ]:
        draw_diagram(Model("Country and Region", "Worldwide", "world"), [
            Region(r, [
                CountryDP(c, vacc_data.get(c["iso_code"], None))
                for c in cs
            ]) for r,cs in continents.items()
        ])

        draw_diagram(Model("Country", "Europe", "europe"), [
            CountryDP(c, vacc_data.get(c["iso_code"], None))
            for c in continents["Europe"]
        ])

        north_america = [
            CountryDP(c, vacc_data.get(c["iso_code"], None))
            for c in continents["North America"]
            if c["iso_code"] != "USA"
        ]
        north_america.append(Region("United States", [
            USStateDP(sd) for sd in vacc_usa_data.values()
        ]))
        draw_diagram(Model("Country and US State", "North America", "north_america"),
            north_america,
        )

        draw_diagram(Model("State", "United States", "usa"), [
            USStateDP(sd) for sd in vacc_usa_data.values()
        ])

        draw_diagram(Model("Country", "Africa", "africa"), [
            CountryDP(c, vacc_data.get(c["iso_code"], None))
            for c in continents["Africa"]
        ])

        draw_diagram(Model("Country", "Asia", "asia"), [
            CountryDP(c, vacc_data.get(c["iso_code"], None))
            for c in continents["Asia"]
        ])

        draw_diagram(Model("Country", "South America", "south_america"), [
            CountryDP(c, vacc_data.get(c["iso_code"], None))
            for c in continents["South America"]
        ])

        draw_diagram(Model("Country", "Oceania", "oce"), [
            CountryDP(c, vacc_data.get(c["iso_code"], None))
            for c in continents["Oceania"]
        ])

        draw_diagram(Model("Country", "Middle East", "middle_east"), [
            CountryDP(c, vacc_data.get(c["iso_code"], None))
            for c in continents["Middle East"]
        ])

if __name__ == "__main__":
    main()
