# JATS* XML Conversion Evaluation

This document aims to explain how the conversion is measured. It is mainly targeted at JATS but can be applied to TEI as well.

## Normalisation

When comparing text we may wish to normalise the content before measuring the how well the text was extracted. The following sections describe common techniques.

### All lower case

Example section title in document:

> INTRODUCTION

Section title in final XML:

> Introduction

In the above case the section title may have produced an all-caps section title in the published document for stylistic reasons. In that case we may not want to peanilse the conversion tool for extracting the all-caps as found in the document. Therefore we can normalise the capitalisation, by converting everything to lower case before comparison.

In this example the text for both, the converted XML and target XML would become:

> introduction

### Whitespace normalisation

Example manuscript title in document:

> Homo naledi, a new species of the genus<br/>
> Homo from the Dinaledi Chamber,<br/>
> South Africa

Manuscript title in final XML:

> Homo naledi, a new species of the genus Homo from the Dinaledi Chamber, South Africa

Both titles are the same but due to the limited page width, line breaks might be added. Similarity, the XML might contain extra whitespaces if it is indented.

All whitepaces (space, line feeds, ...) are replaced with a space and multiple whitespaces are collapsed into a single whitespace.

In this example the text would become:

> Homo naledi, a new species of the genus Homo from the Dinaledi Chamber, South Africa

A text with multiple whitespaces:

> A&nbsp;&nbsp;&nbsp;&nbsp;text&nbsp;&nbsp;&nbsp;&nbsp;with&nbsp;&nbsp;&nbsp;extra&nbsp;&nbsp;&nbsp;&nbsp;space

Would become:

> A text with extra space

### Strip Markup

Using the previous example, the document actually uses the italic type:

> *Homo naledi*, a new species of the genus *Homo* from the Dinaledi Chamber, South Africa

Which is reflected in the XML:

> &lt;i&gt;Homo naledi&lt;/i&gt;, a new species of the genus &lt;i&gt;Homo&lt;/i&gt; from the Dinaledi Chamber, South Africa

In those cases we may want to primarily measure whether the text itself was extracted correctly. How well the markup is reproduced could be seen as a separate concern.

Therefore we will by default strip the markup from the text. For this example it would become:

> Homo naledi, a new species of the genus Homo from the Dinaledi Chamber, South Africa

## Text comparison score

This section describes methods of comparing text. The output is a score between _0.0_ and _1.0_. How that score is reflected may depend on the field and will be explained in another section.

## Exact match

When looking for exact matches, the measure is fairly clear. Either all of the characters match or they don't (after normalisation). The score for any text comparison can only be _1.0_ or _0.0_.

## Fuzzy Match

If say the expected value is:

> Aedes **æ**gypti control in urban areas: A systemic approach to a complex dynamic

and the actual value:

> Aedes **ae**gypti control in urban areas: A systemic approach to a complex dynamic

Using an exact match, this would get zero scores which might set the bar too high.

Instead we might want to calculate a fuzzy match score. The most commen method is to calculate the [Levenshtein distance](https://en.wikipedia.org/wiki/Levenshtein_distance) (edit distance) - "the minimum number of single-character edits (insertions, deletions or substitutions)".

Just looking at the word ("ægypti") that is different the edit distance is _2_:

* "a": substitute with "æ"
* "e": delete
* "gypti": no edit required

How signficant an edit distance is depends on the length of the overall sequence. To get a score between _0.0_ and _1.0_ the edit distance is usually divided by the length of the longest sequence (of the two sequences that we compare) and substracted from _1.0_ to get _1.0_ for a match and _0.0_ for no match.

e.g. for "ægypti" (6 chars) vs "aegypti" (7 chars) the relative score is: `1.0 - 2 / 7 ~= 0.71`

For the whole title (78 chars) we would however get: `1.0 - 2 / 78 = 0.97` (which is significantly higher).

## Conversion scores

This section describes how overall conversion scores are being calculated.

### Binary and multiclass classification scores

This section will introduce some generic classification scores that we will use.

In general we refer to the _target value_ or _expected value_ as the value coming from the reference XML file. Whereas the _actual value_ is coming from the conversion output.

[Binary classifications](https://en.wikipedia.org/wiki/Binary_classification) considers a special case of [multiclass classification](https://en.wikipedia.org/wiki/Multiclass_classification) where the output has only two values, e.g. _0_ and _1_. In that case the _accuracy_ is the percentage of predictions that match the expected value (out of all values). The full definition of accuracy is: sum(true positive) + sum(true negative) / number of samples.

The _accuracy_ can give the wrong impression in particular for imbalanced datasets. In general the [F1 score](https://en.wikipedia.org/wiki/F1_score) is preferred (2 x _precision_ x _recall_ / (_precision_ + _recall_)) (please follow the [Wiki](https://en.wikipedia.org/wiki/F1_score) for a detailed explanation). We will be mainly using the _F1 score_ as well (but we also calculate _precision_ and _recall_).

Scoring [multiclass classification](https://en.wikipedia.org/wiki/Multiclass_classification) is a bit less well defined. Usually each class can be seen as a binary classification. In this case, we may increase _true negative_ every time a class (e.g. title) shouldn't be matched because one of the other classes (e.g. paragraph) should be matched instead. That way the _accuracy_ can increase with every new class without actually getting a better match. That is why in this case the _accuracy_ becomes meaningless, another reason to use the _F1_ score.

### Title

The title is one of the few fields that only exist once which makes it slightly easier to score.

We define *true positive (**tp**)*, *true negative (**tp**)*, *false positive (**fp**)* and *false negative (**fn**)* as follows:

* **tp**: _expected_ and actual are not empty and they match
* **tn**: both _expected_ and _actual_ are empty
* **fp**: _actual_ is not empty and does not match _expected_ (or _expected_ is empty)
* **fn**: _expected_ is not empty and actual does not match _expected_ (or _actual_ is empty)

(This matches the [GROBID PubMed evaluation](https://github.com/kermitt2/grobid/blob/eb9538a1d90b35a87027ff9737a0786f653734c1/grobid-trainer/src/main/java/org/grobid/trainer/evaluation/EndToEndEvaluation.java))

For exact matches that means literarily match (exact match score is 1.0).

For a fuzzy match the common approach is to define a _threshold_ of say _0.80_. If the _fuzzy match score_ is equal or above that _threshold_ we count it as a match. Otherwise no match.

Using the threshold gives us a good indication of whether the mostly matching text was extracted in general. But it would hide cases where the conversion consistently contains small inaccuracies. Therefore it would be good to report on the average fuzzy match score.

### Abstract

Like it is the case for the _title_, most manuscripts have only one _abstract_ and therefore the score will be calculated the same way.

Some manuscripts have more than one abstract, e.g. an abstract in a second language (JATS `trans-abstract`) or multiple `abstract` elements. Each of those is extracted as a separate item of the `abstract` field (`abstract` and `trans-abstract` in document order). With the `string` scoring type the items are concatenated, which only matches if the prediction contains the same abstracts in the same order. The default configuration therefore also scores `abstract` as `partial_ulist`, which matches every abstract individually, regardless of the order (the language order of the PDF often differs from the XML).

However, we want to apply some extra normalisation before comparing the abstract:

* Exclude any formulas (score them separately)

## Lists (authors, section heading, ...)

When comparing lists there may be different aspects that could be measured:

* Ignore order
* Ordered
* All items matched (score 1.0 if all items were matched, 0.0 otherwise)
* Partial match (score between 0.0 and 1.0 depending on how many items were matched)

(GROBID's evaluation implements an _Ordered_ match by concatenating all items; OTS matches individual items and ignores the order)

The suggestion is to report on all four aspects.

Fields that this applies to:

* Authors
* Affiliation
* Section headings
* Figure captions and descriptions
* Table captions and descriptions
* References

## Paragraphs

Paragraphs could be treated as a list of paragraphs. But sometimes the paragraph boundaries are not clear. For example a sentence on the second column could be a seen as a new paragraph or a continuation of the previous paragraph. It is getting even more difficult when considering nested paragraphs.

The suggestion is to treat paragraphs as a single text by concatenating all paragraphs.

Similar to abstract we would also want to exclude:

* Formulas
* Figures
* Tables

**Performance consideration:**

* Levenshtein is slow (_O(n * m)_ - with _n_ and _m_ referring to the length of two sequences)
* PdfAct/icecite use a different diff method (faster)

### Tables

Suggested measures:

* Each cell has to match at the same row and column
* Report on all cells matching and average ratio

### Special characters and words

Special characters and word boundaries are indirectly measured but it will be valuable to explicitly measure their conversion:

* Special characters
* Words (e.g. hyphen breaking words)
* Numbers?
* Units?

### Formulas

TODO

## References

* [GROBID End-to-end evaluation](https://github.com/kermitt2/grobid/blob/master/doc/End-to-end-evaluation.md)
* [GROBID Evaluation results](https://github.com/kermitt2/grobid/blob/master/doc/Benchmarking.md)
