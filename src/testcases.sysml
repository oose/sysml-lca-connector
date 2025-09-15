package testcases {
    private import LCA::*;
    private import Quantities::ScalarQuantityValue;
    attribute def AD1;
    #lcaflow attribute def 'Flow Property1' :> AD1 {
        doc /* this should not be allowed, since AD1 is not a ScalarQuantityValue */
    }
    #lcaflow attribute def 'Flow Property2' :> ScalarQuantityValue;
    #lcaflow attribute Flow1 : 'Flow Property1' {
        @ExternalRef { uuid = "3bccfbd9-cf55-4d2b-b258-f0f13671eea2"; }
    }
    #lcaflow attribute Flow2 : 'Flow Property2' {
        @ExternalRef { uuid = "3bccfbd9-cf55-4d2b-b258-f0f13671eea3"; }
    }
    attribute nonFlow;
    #lca part def 'My Part1' {
        @ExternalRef { uuid = "3bccfbd9-cf55-4d2b-b258-f0f13671eea4"; }
        #exchg attribute f1 :> Flow1 = -42;
        #exchg attribute f2 :> Flow2 = 13;
        #exchg attribute noSubset = 14 {
            doc /* this should not be allowed, since it is not subsetting an lcaFlow */
        }
        #exchg attribute :> nonFlow = 13 {
            doc /* this should not be allowed, since nonFlow is not an lcaFlow */
        }
    }
    part test : 'My Part1';
}