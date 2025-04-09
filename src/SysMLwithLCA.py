# functions to retrieve LCA data from a SysML model
from SysMLModel import SysMLModel

class SysMLLCAModel(SysMLModel):
    LCAPartId=""
    ExchangeId=""
    FlowId=""
    
    def __init__(self, host, project, commit=None):
        print ("SysMLLCAModel: ",host,project,commit)
        super().__init__(host, project, commit)
        self.LCAPartId = self.findElementId(name="LCA-Part", type="MetadataDefinition")
        self.ExchangeId = self.findElementId(name="LCA-Exchange", type="MetadataDefinition")  
        self.FlowId = self.findElementId(name="LCA-Flow", type="MetadataDefinition")

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
            exchanges=self.filterListByMetadata(part['ownedFeature'],self.ExchangeId)
            if exchanges:
                for exchange in exchanges:
                    lcaFlow=self.getSubsettedFeatures(exchange)
                    if lcaFlow and lcaFlow['@id'] in flows:
                        value=self.getDefaultValue(exchange)
                        value['num']=value['num']*factor
                        result.append({'id':flows[lcaFlow['@id']],'name':self.getElement(lcaFlow)['name'],'value':value})
            return result

        result=[]
        flows=self.getFlows()
        lcaParts=self.getElementsWithMetadata("PartDefinition",self.LCAPartId)
        for part in lcaParts.values(): # create an LCA process
            partEntry={"name":part['name'],"exchanges":[]}
            partEntry["exchanges"].extend(getExchangesOfPart(part, flows))
            for subpart in part['ownedPart']:
                subpartEntry=self.getElement(subpart)
                count=self.getMultiplicity(subpartEntry).get('lowerBound',1)# we take the minimal value
                print("Subpart: ",subpartEntry['name'],count,subpartEntry['type'])
                for type in subpartEntry['type']:
                    print("Type: ",type)
                    partDefinition=self.getElement(type)
                    partEntry["exchanges"].extend(getExchangesOfPart(partDefinition, flows, count))
            result.append(partEntry)
        return result

    def getExternalRef(self, element):
        # finds the Metadata with the external reference uuid
        # assumption: the AttributeDefinition has only one MetadataUsage and this is ExternalRef or a substype like lca-flow
        # tbd: select the MetadataUsage typed by LCA-Flow
        # element.ownedMember.feature.ownedMember.value
        return self.getMetaChain(element,[[None,'ownedMember'],['MetadataUsage','feature'],['ReferenceUsage','ownedMember'],['LiteralString','value']])

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
    print(myModel.getProcesses())
    #saveModel(myModel)

# comment this out, if test run successfully
#test()

