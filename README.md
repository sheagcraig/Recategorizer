Recategorizer
=================

Quickly recategorize all policies and packages on a JSS, and then, optionally
(and individually prompted), remove unused categories.

Our organization has used and constructed our JSS rather organically, and at a
certain point we had outgrown our existing category usage. I wrote this script,
based on elements of the
[JSSRecipeCreator](https://github.com/sheagcraig/JSSRecipeCreator) rather
quickly to help in the task of reorganizing.

Recategorizer will first ask you to assign categories to all policies. You will
be offered a chance to bail prior to committing changes. Next, you will be
asked to assign categories to all packages. Again, you may bail prior to
committing changes. Finally, a list of unused categories will be generated,
and you will be prompted individually to keep or delete them.

Recategorizer uses your [AutoPkg](https://github.com/autopkg/autopkg) configuration for [JSSImporter](https://github.com/sheagcraig/JSSImporter), and, if that
doesn't exist, will fall back to using a [python-jss](https://github.com/sheagcraig/python-jss) configuration file.
