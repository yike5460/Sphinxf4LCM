ADD_NSR = """
<config>
    <mano xmlns="http://www.cisco.com/yang/nso/mano/vnfd">
        <nsd xmlns="http://www.cisco.com/yang/nso/mano/nsd">
            <name>%s</name>
            <nsr xmlns="http://cisco.com/yang/nso/tail-f-nsd">
                <name>%s</name>
                <vnfm>%s</vnfm>
                <tenant>%s</tenant>
                <addresses>
                    <connection-point>%s</connection-point>
                    <network-name>%s</network-name>
                    <address>%s</address>
                </addresses>
            </nsr>
        </nsd>
    </mano>
</config>
"""

ADD_NSD = """
<config>
  <mano xmlns="http://www.cisco.com/yang/nso/mano/vnfd">
    <nsd xmlns="http://www.cisco.com/yang/nso/mano/nsd">
      <name>%s</name>
      <flavours>
        <flavour-id>%s</flavour-id>
        <member-vnfs>
          <member-vnf-id>%s</member-vnf-id>
          <vnfd>%s</vnfd>
          <flavour>%s</flavour>
          <vdu>%s</vdu>
        </member-vnfs>
      </flavours>
    </nsd>
  </mano>
</config>
"""
