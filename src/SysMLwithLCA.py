# functions to retrieve LCA data from a SysML model
from SysMLModel import SysMLModel

class SysMLLCAModel(SysMLModel):
    LCAPartId=""
    ExchangeId=""
    FlowId=""
    ExternalRefId=""
    
    def __init__(self, host, project, commit=None):
        print ("SysMLLCAModel: ",host,project,commit)
        super().__init__(host, project, commit)
        self.LCAPartId = self.findElementId(name="LCA-Part", type="MetadataDefinition")
        self.ExchangeId = self.findElementId(name="LCA-Exchange", type="MetadataDefinition")  
        self.FlowId = self.findElementId(name="LCA-Flow", type="MetadataDefinition")
        self.ExternalRefId = self.findElementId(name="ExternalRef", type="MetadataDefinition")

    def getFlows(self):
        # all attributes with metadata LCA-Flow
        # returns {id1:extRef1, id2:extRef2,...}
        result={}
        flows = self.getElementsWithMetadata("AttributeUsage", self.FlowId)
        for flow in flows.values():
            result[flow['@id']]=self.getExternalRef(flow)
        return result        

    def getExchanges(self):  
        # all attributes with LCA-Exchange Metadata
        # returns {id1:exchange1, id2:exchange2,...} 
        return self.getElementsWithMetadata("AttributeUsage", self.ExchangeId)

    def getLCAParts(self):
        # all part definitions with lcapart metadata
        
        def getExchangesOfPart(part, flows, factor=1):
            result=[]
            ownedAttributes=self.getMetaChain(part,[[None,'ownedRelationship'],['FeatureMembership','target']],['AttributeUsage'])
            exchanges=self.filterListByMetadata(ownedAttributes,self.ExchangeId)
            if exchanges:
                for exchange in exchanges:
                    lcaFlow=self.getSubsettedFeatures(exchange)
                    for f in lcaFlow:
                        if  f['@id'] in flows:
                            value=self.getDefaultValue(exchange)
                            value['num']=value['num']*factor
                            result.append({'id':flows[f['@id']],'name':f['declaredName'],'value':value})
                            break # we assume that there is only one LCA-Flow per exchange
            return result

        result=[]
        flows=self.getFlows()
        lcaParts=self.getElementsWithMetadata("PartDefinition",self.LCAPartId)
        for part in lcaParts.values(): # create an LCA process
            partEntry={"name":part['declaredName'],"exchanges":[]}
            partEntry["exchanges"].extend(getExchangesOfPart(part, flows))
            for subpart in part['ownedPart']:
                subpartEntry=self.getElement(subpart)
                count=self.getMultiplicity(subpartEntry).get('lowerBound',1)# we take the minimal value
                print("Subpart: ",subpartEntry['declaredName'],count,subpartEntry.get('type'))
                for type_ref in subpartEntry.get('type', []):
                    print("Type: ",type_ref)
                    partDefinition=self.getElement(type_ref)
                    partEntry["exchanges"].extend(getExchangesOfPart(partDefinition, flows, count))
            result.append(partEntry)
        return result
    
    def getExternalRef(self, element):
        # finds the Metadata with the external reference uuid
        # assumption: the AttributeDefinition has only one MetadataUsage and this is ExternalRef or a substype like lca-flow
        # element.ownedMember.feature.ownedMember.value
        metadataUsage = self.getMetaChain(element,[[None,'ownedRelationship'],['OwningMembership','target']],['MetadataUsage'])
        # tbd:filter those that are typed by ExternalRef
        feature = self.getMetaChain(metadataUsage,[[None,'ownedRelationship']],['FeatureMembership'])
        if feature:
            feature = [f for f in feature if f.get('memberName') == 'uuid']
        
            #print("getExternalRef: ", element['declaredName'],self.getMetaChain(feature,[[None,'target'],
            #                                ['ReferenceUsage','ownedRelationship'],['FeatureValue','target'],
            #                                ['LiteralString','value']])[0])
            return self.getMetaChain(feature,[[None,'target'],
                                            ['ReferenceUsage','ownedRelationship'],['FeatureValue','target'],
                                            ['LiteralString','value']])[0]
        else:
            return None
        # return self.getMetaChain(element,[[None,'ownedMember'],['MetadataUsage','feature'],['ReferenceUsage','ownedMember'],['LiteralString','value']])
        # this only works if the repository contains derived values.
 
    def getExternalRef1(self, element):
        # element.ownedMember.feature.ownedMember.value
        # not using the generic getMetaChain method
        if element['@type']=="AttributeDefinition":  
            for member in element['ownedMember']:
                
                metadataUsage=self.theModel[member['@id']]
                if metadataUsage['@type'] == "MetadataUsage":
                    for feature in metadataUsage['feature']:
                
                        referenceUsage=self.theModel[feature['@id']]
                        if referenceUsage['@type'] == "ReferenceUsage":
                            for featureValue in referenceUsage['ownedMember']:
                          
                                literalString=self.theModel[featureValue['@id']]
                                if literalString['@type'] == "LiteralString":
                                    return literalString['value']
                        

def saveModel(myModel):
    s=myModel.asHTML()
    with open("theModel.html", 'w',encoding='utf-8') as file:                    
        file.write(s)


def test():
    myModel= SysMLLCAModel("http://sysml2.intercax.com:9000", "fe52af83-5382-4d39-9d60-91239a3e4dba")
    print("Projectname: ",myModel.name)
    #print("Flows:")
    #print(myModel.getFlows())
    #for flow in myModel.getFlows().values():
    #   print(flow['@id'],flow['name'], myModel.getExternalRef(flow))
    #print (myModel.getMetaChain(myModel.getElementbyId("017b7263-f1a4-4cde-9589-734d4718744b"),[['AttributeDefinition','ownedMember'],['MetadataUsage','feature'],['ReferenceUsage','ownedMember'],['LiteralString','value']]))
    print(myModel.getLCAParts())
    #saveModel(myModel)

# comment this out, if test run successfully
#test()

