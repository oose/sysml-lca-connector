# sysml-lca-connector
A utility to exchange data between the tool openLCA and any SysML 2 repository that offers the standard REST-API.

See the [presentation](https://github.com/oose/sysml-lca-connector/blob/main/doc/automating%20LCA%20using%20the%20SysML%202%20API%20(LearnMBSE%20presentation).pdf) for more details or the paper on [Automated Life Cycle Assessment Using the Systems Modeling Language v2 and OpenLCA](https://ieeexplore.ieee.org/abstract/document/11083801) published by IEEE. 

An online presentation and demo has been recorded by INCOSE Brasil and is available here:

[![YouTube-Video](https://img.youtube.com/vi/CjHNEuF5HQw/0.jpg)](https://www.youtube.com/watch?v=CjHNEuF5HQw)

## Installation

Simply download the zip-File from the [⇩ latest release](https://github.com/oose/sysml-lca-connector/releases/latest)
and unpack it.

You will need an installation of **openLCA** and a **SysML 2 authoring tool** with API.
- [openLCA](https://www.openlca.org/download-form/)
- SysML 2 authoring tool options
  - hosted pilot implementation
    - [SysML 2 pilot implementation juypter lab ](https://www.sysmlv2lab.com)  
    This webbased tool can publish the model to a public repository with the API under [sysml2.intercax.com:9000](http://sysml2.intercax.com:9000/docs/#)
  - You can set up the pilot implementation locally
    - [SysML-v2-Release](https://github.com/Systems-Modeling/SysML-v2-Release)
    - [SysML-v2-API-Services](https://github.com/Systems-Modeling/SysML-v2-API-Services)
