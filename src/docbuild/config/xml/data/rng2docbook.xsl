<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:rng="http://relaxng.org/ns/structure/1.0"
    xmlns:db="http://docbook.org/ns/docbook"
    xmlns:a="http://relaxng.org/ns/compatibility/annotations/1.0"
    xmlns="http://docbook.org/ns/docbook"
    exclude-result-prefixes="rng db a">

  <xsl:output method="xml" encoding="UTF-8" indent="yes"/>
  <xsl:strip-space elements="*"/>

  <!-- Lookup for patterns by @name (e.g. ds.product) -->
  <xsl:key name="k-define-by-name" match="rng:define" use="@name"/>

  <!-- Root: RNG grammar -> DocBook 5 reference -->
  <xsl:template match="/rng:grammar">
    <article xmlns="http://docbook.org/ns/docbook" version="5.0">
      <info>
        <title>
          <xsl:choose>
            <xsl:when test="db:refname">
              <xsl:value-of select="db:refname[1]"/>
            </xsl:when>
            <xsl:otherwise>Schema Reference</xsl:otherwise>
          </xsl:choose>
        </title>
      </info>

      <!-- Start pattern first -->
      <xsl:apply-templates select="rng:start"/>

      <!-- Then traverse reachable patterns starting from <start/> -->
      <xsl:apply-templates select="rng:start" mode="walk"/>
    </article>
  </xsl:template>

  <!-- Helper: compute a human-readable name for a pattern -->
  <xsl:template name="pattern-name">
    <xsl:param name="node" select="."/>
    <!-- Prefer enclosing div/db:refname if present -->
    <xsl:variable name="blockname" select="$node/ancestor::rng:div[db:refname][1]/db:refname[1]"/>
    <xsl:choose>
      <xsl:when test="string($blockname)">
        <xsl:value-of select="$blockname"/>
      </xsl:when>
      <xsl:when test="$node/db:refname">
        <xsl:value-of select="$node/db:refname[1]"/>
      </xsl:when>
      <xsl:when test="name($node) = 'start'">start</xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="$node/@name"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- Helper: compute a description/refpurpose -->
  <xsl:template name="pattern-purpose">
    <xsl:param name="node" select="."/>
    <xsl:variable name="blockpurpose" select="$node/ancestor::rng:div[db:refpurpose][1]/db:refpurpose[1]"/>
    <xsl:choose>
      <xsl:when test="string($blockpurpose)">
        <xsl:value-of select="$blockpurpose"/>
      </xsl:when>
      <xsl:when test="$node/db:refpurpose">
        <xsl:value-of select="$node/db:refpurpose[1]"/>
      </xsl:when>
      <xsl:when test="$node/a:documentation">
        <xsl:value-of select="$node/a:documentation[1]"/>
      </xsl:when>
      <xsl:otherwise/>
    </xsl:choose>
  </xsl:template>

  <!-- Helper: compute a description for an attribute -->
  <xsl:template name="attribute-purpose">
    <xsl:param name="attr" select="."/>
    <xsl:choose>
      <!-- Prefer attribute-level DocBook purpose, then annotation documentation -->
      <xsl:when test="$attr/db:refpurpose">
        <xsl:value-of select="$attr/db:refpurpose[1]"/>
      </xsl:when>
      <xsl:when test="$attr/a:documentation">
        <xsl:value-of select="$attr/a:documentation[1]"/>
      </xsl:when>
      <!-- Fall back to enclosing define's purpose, if any -->
      <xsl:when test="$attr/ancestor::rng:define[db:refpurpose][1]">
        <xsl:value-of select="$attr/ancestor::rng:define[db:refpurpose][1]/db:refpurpose[1]"/>
      </xsl:when>
      <xsl:otherwise/>
    </xsl:choose>
  </xsl:template>

  <!-- Helper: compute xml:id from db:refname (fallback to @name) -->
  <xsl:template name="pattern-id">
    <xsl:param name="node" select="."/>
    <!-- Use the RNG pattern @name (or 'start') for a stable NCName-based id -->
    <xsl:text>rnc.</xsl:text>
    <xsl:choose>
      <xsl:when test="name($node) = 'start'">start</xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="$node/@name"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- Refentry for <start> -->
  <xsl:template match="rng:start">
    <xsl:variable name="id">
      <xsl:call-template name="pattern-id">
        <xsl:with-param name="node" select="."/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="name">
      <xsl:call-template name="pattern-name">
        <xsl:with-param name="node" select="."/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="purpose">
      <xsl:call-template name="pattern-purpose">
        <xsl:with-param name="node" select="."/>
      </xsl:call-template>
    </xsl:variable>

    <refentry role="{$id}">
      <refnamediv>
        <refname><xsl:value-of select="$name"/></refname>
        <refpurpose><xsl:value-of select="$purpose"/></refpurpose>
      </refnamediv>
      <refsynopsisdiv>
        <title>Content Model</title>
        <synopsis>
          <xsl:value-of select="$name"/>
          <xsl:text> ::= </xsl:text>
          <!-- Format the content model -->
          <xsl:apply-templates select="rng:*" mode="syn"/>
        </synopsis>
      </refsynopsisdiv>
    </refentry>
  </xsl:template>

  <!-- Refentry for each <define> -->
  <!-- Logical element blocks: defines with an element child inside a refname'ed div -->
  <xsl:template match="rng:define[parent::rng:div[db:refname] and rng:element]" mode="entry">
    <xsl:variable name="id">
      <xsl:call-template name="pattern-id">
        <xsl:with-param name="node" select="."/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="name">
      <xsl:call-template name="pattern-name">
        <xsl:with-param name="node" select="."/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="purpose">
      <xsl:call-template name="pattern-purpose">
        <xsl:with-param name="node" select="."/>
      </xsl:call-template>
    </xsl:variable>

    <refentry role="{$id}">
      <refnamediv>
        <refname><xsl:value-of select="$name"/></refname>
        <refpurpose><xsl:value-of select="$purpose"/></refpurpose>
      </refnamediv>
      <refsynopsisdiv>
        <title>Content Model</title>
        <synopsis>
          <xsl:value-of select="$name"/>
          <xsl:text> ::= </xsl:text>
          <xsl:apply-templates select="rng:*" mode="syn"/>
        </synopsis>
      </refsynopsisdiv>

      <!-- Attribute overview for this element, if any -->
      <xsl:call-template name="emit-attributes">
        <xsl:with-param name="node" select="."/>
      </xsl:call-template>
    </refentry>
  </xsl:template>

  <!-- Emit an attribute list for the logical element represented by a define -->
  <xsl:template name="emit-attributes">
    <xsl:param name="node" select="."/>

    <!-- Element context for this logical unit -->
    <xsl:variable name="elem" select="$node//rng:element[1]"/>

    <!-- Direct attributes on the element (or nested inside) -->
    <xsl:variable name="attrs-direct" select="$elem//rng:attribute"/>

    <!-- Attributes coming from referenced attribute patterns (e.g., ds.*.attr) -->
    <xsl:variable name="attrs-from-ref"
            select="key('k-define-by-name', $elem//rng:ref/@name)//rng:attribute"/>

    <!-- Combined attribute set for this element -->
    <xsl:variable name="attrs" select="$attrs-direct | $attrs-from-ref"/>

    <xsl:if test="$attrs">
      <refsection role="attributes">
        <title>Attributes</title>
        <variablelist>
          <xsl:for-each select="$attrs">
            <varlistentry>
              <term>
                <code>
                  <xsl:text>@</xsl:text>
                  <xsl:value-of select="@name"/>
                </code>
                <!-- Underlying data type (if any) -->
                <xsl:variable name="dtype">
                  <xsl:choose>
                    <!-- Direct data type on this attribute -->
                    <xsl:when test="rng:data/@type">
                      <xsl:value-of select="rng:data[1]/@type"/>
                    </xsl:when>
                    <!-- Data type from a referenced type definition (e.g., ds.type.*) -->
                    <xsl:when test="rng:ref">
                      <xsl:variable name="tdef" select="key('k-define-by-name', rng:ref[1]/@name)[1]"/>
                      <xsl:value-of select="$tdef//rng:data[1]/@type"/>
                    </xsl:when>
                    <xsl:otherwise/>
                  </xsl:choose>
                </xsl:variable>
                <xsl:if test="@a:defaultValue">
                  <xsl:text> (default: </xsl:text>
                  <literal>
                    <xsl:value-of select="@a:defaultValue"/>
                  </literal>
                  <xsl:text>)</xsl:text>
                </xsl:if>
                <xsl:if test="string($dtype)">
                  <xsl:text> [type: </xsl:text>
                  <literal>
                    <xsl:value-of select="$dtype"/>
                  </literal>
                  <xsl:text>]</xsl:text>
                </xsl:if>
              </term>
              <listitem>
                <para>
                  <xsl:call-template name="attribute-purpose">
                    <xsl:with-param name="attr" select="."/>
                  </xsl:call-template>
                </para>

                <!-- Enumerated allowed values, if any, as an itemized list -->
                <xsl:variable name="vals" select=".//rng:choice/rng:value"/>
                <xsl:if test="$vals">
                  <itemizedlist>
                    <xsl:for-each select="$vals">
                      <listitem>
                        <para>
                          <literal>
                            <xsl:value-of select="."/>
                          </literal>
                          <!-- Per-value documentation, if available as following a:documentation sibling -->
                          <xsl:variable name="valdoc" select="following-sibling::*[self::a:documentation][1]"/>
                          <xsl:if test="$valdoc">
                            <xsl:text>: </xsl:text>
                            <xsl:value-of select="$valdoc"/>
                          </xsl:if>
                        </para>
                      </listitem>
                    </xsl:for-each>
                  </itemizedlist>
                </xsl:if>
              </listitem>
            </varlistentry>
          </xsl:for-each>
        </variablelist>
      </refsection>
    </xsl:if>
  </xsl:template>

  <!-- ===== Traversal starting at <start/> (mode=walk) ===== -->

  <!-- Default walk: descend into RNG structure, carrying visited set -->
  <xsl:template match="*" mode="walk">
    <xsl:param name="visited"/>
    <xsl:apply-templates select="rng:*" mode="walk">
      <xsl:with-param name="visited" select="$visited"/>
    </xsl:apply-templates>
  </xsl:template>

  <xsl:template match="rng:start" mode="walk">
    <xsl:param name="visited"/>
    <xsl:apply-templates select="rng:*" mode="walk">
      <xsl:with-param name="visited" select="$visited"/>
    </xsl:apply-templates>
  </xsl:template>

  <xsl:template match="rng:ref" mode="walk">
    <xsl:param name="visited"/>
    <xsl:variable name="target" select="@name"/>
    <xsl:variable name="def" select="key('k-define-by-name', $target)[1]"/>
    <xsl:variable name="seen" select="contains(concat(' ', $visited, ' '), concat(' ', $target, ' '))"/>

    <!-- Emit one refentry per reachable logical element (first ref only) -->
    <xsl:if test="$def and (not($seen)) and $def[parent::rng:div[db:refname] and rng:element] and not(preceding::rng:ref[@name = $target])">
      <xsl:apply-templates select="$def" mode="entry"/>
    </xsl:if>

    <!-- Continue walking into the referenced pattern -->
    <xsl:if test="$def and not($seen)">
      <xsl:apply-templates select="$def/rng:*" mode="walk">
        <xsl:with-param name="visited" select="concat(normalize-space($visited), ' ', $target)"/>
      </xsl:apply-templates>
    </xsl:if>
  </xsl:template>

  <!-- ===== Content model formatting (mode="syn") ===== -->

  <!-- Default: recurse into children -->
  <xsl:template match="*" mode="syn">
    <xsl:apply-templates select="rng:*" mode="syn"/>
  </xsl:template>

  <!-- Attributes are not part of the synopsis content model -->
  <xsl:template match="rng:attribute" mode="syn"/>

  <!-- Reference to another pattern: -> DocBook link -->
  <xsl:template match="rng:ref" mode="syn">
    <xsl:variable name="target" select="@name"/>
    <xsl:variable name="def" select="key('k-define-by-name', $target)[1]"/>
    <!-- Skip references that resolve only to attribute patterns (no elements) -->
    <xsl:if test="not($def) or $def//rng:element">
      <xsl:variable name="tname">
        <xsl:choose>
          <!-- Prefer the concrete element name, then any db:refname, then pattern name -->
          <xsl:when test="$def/rng:element/@name">
            <xsl:value-of select="$def/rng:element[1]/@name"/>
          </xsl:when>
          <xsl:when test="$def/db:refname">
            <xsl:value-of select="$def/db:refname[1]"/>
          </xsl:when>
          <xsl:otherwise>
            <xsl:value-of select="$target"/>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:variable>
      <xsl:variable name="tid">
        <xsl:call-template name="pattern-id">
          <xsl:with-param name="node" select="$def"/>
        </xsl:call-template>
      </xsl:variable>

      <link linkend="{$tid}">
        <xsl:value-of select="$tname"/>
      </link>
    </xsl:if>
  </xsl:template>

  <!-- Element: just show its name for now -->
  <xsl:template match="rng:element" mode="syn">
    <!-- Non-attribute child patterns of this element (its content model) -->
    <xsl:variable name="children" select="rng:*[
      not(self::rng:attribute)
      and not(self::rng:interleave)
      and (
        .//rng:element
        or .//rng:ref[key('k-define-by-name', @name)//rng:element]
      )
    ]"/>

    <xsl:choose>
      <!-- If there is no structured content (only attributes/empty/text), show 'text' -->
      <xsl:when test="not($children)">
        <xsl:text>text</xsl:text>
      </xsl:when>
      <xsl:otherwise>
        <xsl:for-each select="$children">
          <xsl:if test="position() &gt; 1">
            <!-- newline + indentation for subsequent items -->
            <xsl:text>&#10;        </xsl:text>
          </xsl:if>
          <xsl:apply-templates select="." mode="syn"/>
          <xsl:if test="position() != last()">
            <xsl:text>,</xsl:text>
          </xsl:if>
        </xsl:for-each>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- Data / value: show type or literal -->
  <xsl:template match="rng:data" mode="syn">
    <xsl:text>data(</xsl:text>
    <xsl:value-of select="@type"/>
    <xsl:text>)</xsl:text>
  </xsl:template>

  <xsl:template match="rng:value" mode="syn">
    <xsl:text>"</xsl:text>
    <xsl:value-of select="."/>
    <xsl:text>"</xsl:text>
  </xsl:template>

  <!-- choice(a,b,...) -> a | b | ... -->
  <xsl:template match="rng:choice" mode="syn">
    <xsl:for-each select="rng:*[not(self::rng:attribute)]">
      <xsl:apply-templates select="." mode="syn"/>
      <xsl:if test="position() != last()">
        <xsl:text> | </xsl:text>
      </xsl:if>
    </xsl:for-each>
  </xsl:template>

  <!-- group(a,b,...) -> a , b , ... -->
  <xsl:template match="rng:group" mode="syn">
    <!-- Only show groups that ultimately contain element-bearing content -->
    <xsl:variable name="children" select="rng:*[
      not(self::rng:attribute)
      and (
        .//rng:element
        or .//rng:ref[key('k-define-by-name', @name)//rng:element]
      )
    ]"/>

    <xsl:if test="$children">
      <xsl:text>(</xsl:text>
      <xsl:for-each select="$children">
        <xsl:apply-templates select="." mode="syn"/>
        <xsl:if test="position() != last()">
          <xsl:text>, </xsl:text>
        </xsl:if>
      </xsl:for-each>
      <xsl:text>)</xsl:text>
    </xsl:if>
  </xsl:template>

  <!-- interleave(a,b,...) -> a & b & ... -->
  <xsl:template match="rng:interleave" mode="syn">
    <xsl:for-each select="rng:*[not(self::rng:attribute)]">
      <xsl:apply-templates select="." mode="syn"/>
      <xsl:if test="position() != last()">
        <xsl:text> &amp; </xsl:text>
      </xsl:if>
    </xsl:for-each>
  </xsl:template>

  <!-- Quantifiers -->
  <xsl:template match="rng:oneOrMore" mode="syn">
    <!-- Only render if this wrapper ultimately contains element-bearing content -->
    <xsl:if test=".//rng:element or .//rng:ref[key('k-define-by-name', @name)//rng:element]">
      <xsl:apply-templates select="rng:*" mode="syn"/>
      <xsl:text>+</xsl:text>
    </xsl:if>
  </xsl:template>

  <xsl:template match="rng:zeroOrMore" mode="syn">
    <!-- Only render if this wrapper ultimately contains element-bearing content -->
    <xsl:if test=".//rng:element or .//rng:ref[key('k-define-by-name', @name)//rng:element]">
      <xsl:apply-templates select="rng:*" mode="syn"/>
      <xsl:text>*</xsl:text>
    </xsl:if>
  </xsl:template>

  <xsl:template match="rng:optional" mode="syn">
    <!-- Only render if this wrapper ultimately contains element-bearing content -->
    <xsl:if test=".//rng:element or .//rng:ref[key('k-define-by-name', @name)//rng:element]">
      <xsl:apply-templates select="rng:*" mode="syn"/>
      <xsl:text>?</xsl:text>
    </xsl:if>
  </xsl:template>

</xsl:stylesheet>
