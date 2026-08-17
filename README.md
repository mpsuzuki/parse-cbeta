# parse-cbeta

parser of CBETA XML to analyze the range of each volume
in XML file.

## Why?
**To identify the internal volume number of each sutra, from the
T-location number.**

The **Taisho Tripitaka** is a huge collection of Buddhism Sutra
and related documents, and all lines in the Taisho Tripitaka
can have their location identifiers by the sequential text
number (assigned to each sutra), the binding number,
the page number (in each binding), the row index, and
the line number, like ```T0123A.45.7890b12```.
Here, **T0123A** is the text number, **45** is the binding number,
**7890** is the page number (in each binding), **b** is the
row index (a, b, and c), and **12** is the line number.

Although this location identifier should be sufficient
to spot the volume number in each text, but this location
number system does not provide it directly.

This parser is designed to retrieve such information by
parsing the XML data file coded by **CBETA** project.

## How to use?

### Generate the segment database
```
./parse-cbeta.py --output cbeta-segment.json --dir cbeta/xml-p5/T/
```

would generate the segment database (in JSON format) from
the XML files stored under ```cbeta/xml-p5/T/```.

```
./summarize-cbeta-segments.py --json cbeta-segments.json
```

would print the pairing status of
```<cb:juan fun="open">``` and ```<cb:juan fun="close">```.

### To do

* Check the ```n``` attributes in ```<cb:juan>``` elements are well sequential and no gaps in them.
* Check the text tagged by *open* element and *close* elements are sufficiently similar.
* Identify the numbering system of the each volumes: [一, 二, 三, ...], [上, 中, 下], [天, 地, 玄, ...], etc.  


