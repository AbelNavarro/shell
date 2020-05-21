#!/bin/bash

curl -s $1 | grep article_body | sed 's/^.*article_body//' | head -n 1 | sed 's/^.*dark"><p class="">//' | sed 's/<\/b.*//' | sed 's/<\/p><p class="">/\n\n/g' | head -n -2
