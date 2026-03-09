<?xml version="1.0" encoding="UTF-8"?>
<!--
  Purpose:
    XSLT stylesheet to convert product configuration (version 6) to
    new portal configuration (version 7)

  Input:
    - product configuration XML file (version 6)
    - Stitchfile

  Output:
    - portal configuration XML file (version 7)

  Parameters:
    - None / TBD

  Author:
    Tom Schraitle

  Copyright (C) 2026 SUSE Linux GmbH
-->
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xi="http://www.w3.org/2001/XInclude"
  xmlns:exsl="http://exslt.org/common"
  exclude-result-prefixes="exsl">

  <xsl:output encoding="UTF-8" indent="yes" method="xml"/>
  <xsl:preserve-space elements="*"/>

  <!-- ======== Parameters -->
  <xsl:param name="use.xincludes" select="true()" />

  <!-- ======== Keys -->
  <!-- Define a key to group <language> elements by their @lang attribute -->
  <xsl:key name="langKey" match="category/language[not(ancestor-or-self::product)]" use="@lang" />

  <!-- ======== Variables -->
  <xsl:variable name="_transformation-map">
    <config>
      <product id="appliance" series="pas" family="linux" rank="04150" />
      <product id="cloudnative" series="pas" family="cn" rank="00030" />
      <product id="container" series="pas" family="linux" rank="04130" />
      <product id="compliance" series="pas" family="linux" rank="" />
      <product id="liberty" series="pas" family="linux" rank="00060" />
      <product id="releasenotes" series="rn" family="linux" />
      <product id="sbp" series="sbp" family="linux" />
      <product id="ses" series="pas" family="linux" rank="04160" />
      <product id="sled" series="pas" family="linux" rank="04100" />
      <product id="sle-ha" series="pas" family="linux" rank="04070" />
      <product id="sle-hpc" series="pas" family="linux" rank="04110" />
      <product id="sle-micro" series="pas" family="linux" rank="00020" />
      <product id="sle-public-cloud" series="pas" family="linux" rank="04060" />
      <product id="sle-rt" series="pas" family="linux" rank="04080" />
      <product id="sles-sap" series="pas" family="linux" rank="00050" />
      <product id="sles" series="pas" family="linux" rank="00080" />
      <product id="sle-vmdp" series="pas" family="linux" rank="04120" />
      <product id="smart" series="pas" family="linux" />
      <product id="smt" series="pas" family="linux" rank="04330" />
      <product id="soc" series="pas" family="linux" rank="04300" />
      <product id="style" series="pas" family="linux" />
      <product id="subscription" series="pas" family="linux" rank="04140" />
      <product id="suma-retail" series="pas" family="linux" />
      <product id="suma" series="pas" family="linux" rank="" />
      <product id="suma-ai" series="pas" family="suse-ai" rank="00010" />
      <product id="suma-caasp" series="pas" family="linux" rank="04310" />
      <product id="suma-cap" series="pas" family="linux" rank="04320"/>
      <product id="suma-distribution-migration-system" series="pas" family="linux" />
      <product id="suma-edge" series="pas" family="suse-edge" rank="00040" />
      <product id="trd" series="trd" family="linux" />
    </config>
  </xsl:variable>
  <xsl:variable name="config" select="exsl:node-set($_transformation-map)/*" />


  <!-- ======== General Templates -->
  <xsl:template match="node() | @*" name="copy">
      <xsl:copy>
        <xsl:apply-templates select="node() | @*" />
      </xsl:copy>
  </xsl:template>


  <!-- ========  Ignore Templates -->
  <xsl:template match="/docservconfig/hashes"/>


  <!-- ========  Templates -->
  <xsl:template match="/docservconfig">
    <portal schemaversion="7.0" xmlns:xi="http://www.w3.org/2001/XInclude">
      <xsl:apply-templates select="categories" />
      <productfamilies>
        <item id="linux">Linux</item>
        <item id="cn">Cloud Native</item>
        <item id="suse-edge">SUSE Edge</item>
        <item id="suse-ai">SUSE AI</item>
      </productfamilies>
      <series>
        <item id="pas">Products &amp; Solutions</item>
        <item id="sbp" >SUSE Best Practices</item>
        <item id="trd">Technical References</item>
        <item id="rn">Release Notes</item>
      </series>
      <xsl:apply-templates select="*[not(self::categories)]" />
    </portal>
  </xsl:template>

  <xsl:template match="/docservconfig/categories">
    <xsl:copy>
      <!-- 1. Select only the first occurring <language> element for each unique @lang -->
      <xsl:for-each select="category/language[generate-id() = generate-id(key('langKey', @lang)[2])]">

        <!-- Store the current language code -->
        <xsl:variable name="currentLang" select="@lang" />

        <!-- Create the new <category> element grouped by language -->
        <xsl:text>&#10;  </xsl:text>
        <category lang="{$currentLang}">

          <!-- Convert default="1" to default="true" to match your target XML -->
          <xsl:if test="@default = '1'">
            <xsl:attribute name="default">true</xsl:attribute>
          </xsl:if>

          <!-- 3. Retrieve all <language> elements that match the current @lang -->
          <xsl:for-each select="key('langKey', $currentLang)">
            <!-- Create an <entry> for each, pulling categoryid from its parent -->
             <xsl:text>&#10;    </xsl:text>
            <entry categoryid="{../@categoryid}" title="{@title}" />
          </xsl:for-each>
          <xsl:text>&#10;  </xsl:text>
        </category>
      </xsl:for-each>
      <xsl:text>&#10;</xsl:text>
    </xsl:copy>
    <xsl:text>&#10;  </xsl:text>
  </xsl:template>

  <!-- Product  -->
  <xsl:template match="product">
    <xsl:variable name="id" select="@productid" />
    <xsl:variable name="cnfg" select="$config/product[@id=$id]" />
    <!-- <xsl:variable name="filename" select="concat($id, '.xml')" />

    <xi:include href="{$filename}" />
-->

    <xsl:copy>
      <xsl:apply-templates select="@*" />
      <!-- Add new attributes based on the transformation map -->
      <xsl:attribute name="family">
        <xsl:value-of select="$cnfg/@family" />
      </xsl:attribute>
      <xsl:attribute name="series">
        <xsl:value-of select="$cnfg/@series" />
      </xsl:attribute>
      <xsl:attribute name="rank">
        <xsl:value-of select="$cnfg/@rank" />
      </xsl:attribute>
      <xsl:apply-templates />
    </xsl:copy>
  </xsl:template>

  <!-- don't copy these attributes -->
  <xsl:template match="product/@schemaversion" />
  <xsl:template match="product/@site-section" />

  <xsl:template match="product/@productid">
    <xsl:variable name="id" select="." />
    <xsl:attribute name="id">
      <xsl:value-of select="$id" />
    </xsl:attribute>
  </xsl:template>


  <!-- docset  -->
  <xsl:template match="docset/@setid">
    <xsl:variable name="id" select="." />
    <xsl:attribute name="id">
      <xsl:value-of select="$id"/>
    </xsl:attribute>
  </xsl:template>

</xsl:stylesheet>
