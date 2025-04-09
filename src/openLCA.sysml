package openLCA{
doc /* defines the elements corresponding to openLCA Objects
 * LCA:         SysML 2             SysML 1 
 * flow: attribute being typed by a flow property (v1: attribute typed by a ValueType)
 * flow property: attribute definition specializing ScalarQuantityValue (v1: ValueType)
 * unit group: MeasurementUnit (v1: Unit)
 * */
private import ScalarValues::String;
private import ScalarValues::Integer;
private import Quantities::ScalarQuantityValue;
public import SI::*;
private import MeasurementReferences::CountValue;
private import Metaobjects::SemanticMetadata;

metadata def ExternalRef{
    doc /* this declares an element as a reference to an external object, identified by a uuid */
    attribute uuid:String;
}

metadata def <lcaflow> 'LCA-Flow':> SemanticMetadata, ExternalRef{
    doc /* this declares an attribute as an lca-flow, to be subsetted by 
    exchange-attributes of parts and part definitions.
    Must be defined at the package level (i.e. as attribute of Anything) */
    subsets annotatedElement: SysML::AttributeUsage;
}

metadata def <exchg> 'LCA-Exchange'{
    doc /* this declares an attribute as quantifing an exchange with the 
    environment during the production of the element. 
    A positive value is output, a negative value is input.
    Must be owned by a part or part def.*/
    subsets annotatedElement: SysML::AttributeUsage;
    // must subset an lcaflow. (I don't know how to enforce this)
}

metadata def <lca> 'LCA-Part' specializes ExternalRef{
    doc /* this declares a part (definition) as something that will have a process in an lca-tool, 
    whose impact can be analyzed. 
    In a first step, the process can be generated in the lca-tool and the id will be recorded. 
    The result of the calculation will then be added as an attribute, so that the impact can 
    guide the system design activities. */
    subsets annotatedElement: SysML::PartUsage;
    subsets annotatedElement: SysML::PartDefinition;
}

/* mappings to QuantityValues from the elcd database or new definitions*/
alias 'Number of items' for CountValue;
alias Length for LengthValue;
alias Area for AreaValue ;
alias Volume for VolumeValue;
alias Mass for MassValue;
alias Energy for EnergyValue ;
attribute def 'Net calorific value':> EnergyValue ;
attribute def 'Gross calorific value':> EnergyValue ;
alias Radioactivity for NuclearActivityValue ;
attribute def 'Area*time':> ScalarQuantityValue ;
}

/* example
#lcaflow attribute 'Flow1' : 'Flow Property1'{
	@ExternalRef{uuid="3bccfbd9-cf55-4d2b-b258-f0f13671eea2";}
}
#lcaflow attribute 'Flow2' : 'Flow Property1'{
	@ExternalRef{uuid="3bccfbd9-cf55-4d2b-b258-f0f13671eea3";}
}

#lcaflow attribute def 'Flow Property1':>'Number of items';

#lca part def 'My Part1' {
	@ExternalRef{uuid="3bccfbd9-cf55-4d2b-b258-f0f13671eea4";} // process "produce My Part1"
    #exchg subsets Flow1 =-42; // consumed when producing one item of My Part1
    #exchg subsets Flow2 =13; // produced when producing one item of My Part1
}
// example end*/

