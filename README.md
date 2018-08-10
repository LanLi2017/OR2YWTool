# OR2YWTool
Openrefine to Yesworkflow model tool
====================================

The Openrefine to Yesworkflow model(OR2YW) toolkit repository contains or2yw-examples folder,in which uses Ecology_Rodents dataset and NYPL(New York Public Library) Menu dataset as examples.

**[Yesworkflow](https://github.com/yesworkflow-org/yw-prototypes)**.

**[Openrefine](http://openrefine.org/)**.

Overview
--------

This tool aims to provide an auto-parsing method from Openrefine Operation History JSON file to Yesworklfow model. As we know, the openrefine operation history json file works as a data wrangling workflow. However, the structure of the workflow is not transparent enough, where we can not know the dependency and independency of column operations. And through yw model, it classify Openrefine operations into two levels: schema level and column level. 

1.Folder Structure
------------------
Take Ecology_rodents folder as an example:

folder        |  Function
--------------|------------
dataset       |  "messy dataset"
facts         |  "File for storing prolog facts about scripts"
gv            |  Save the DOT output to a file
pdf           |  Render gv file as PDF file using Graphviz's dot command
png           |  Render gv file as PNG file using Graphviz's dot command
results       |  
script        |  Auto-parsing file: Linear/Serial-Parallell and the Openrefine json file
yw            |  The parsed yw comments
yw.properties |  yw settings for graph(yw) command
yw_generate.sh|  cheatsheet command

2.Toolkit Usage
----------------
1.Go to ../../script/ConfigTool.py; This config file is for users to choose whether to generate Linear or Serial-Parallel yw model. 




