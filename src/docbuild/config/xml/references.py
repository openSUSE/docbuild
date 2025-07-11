"""Check <ref/> links on a stitched XML configuration file."""

from lxml import etree


def check_ref_to_subdeliverable(
    ref: etree._Element,
    attrs: dict[str, str],
) -> str | None:
    """Check reference to a subdeliverable."""
    product = attrs.get('product')
    docset = attrs.get('docset')
    dc = attrs.get('dc')
    subdeliverable = attrs.get('subdeliverable')
    # Build the XPath
    xpath = (  # Use // to be more robust against nesting
        f'//product[@productid = {product!r}]/docset[@setid = {docset!r}]'
        f"/builddocs/language[@default = 'true' or @default = 1]"
        f"/deliverable[dc = '{dc}'][subdeliverable = '{subdeliverable}']"
    )

    if not ref.getroottree().xpath(xpath):
        origin = ref.xpath(
            'concat(ancestor::product/@productid, "/",  ancestor::docset/@setid)'
        )
        return (
            f'Failed reference from {origin!r} to '
            f'{product}/{docset}:{dc}#{subdeliverable}: '
            'Referenced subdeliverable does not exist.'
        )


def check_ref_to_deliverable(ref: etree._Element, attrs: dict[str, str]) -> str | None:
    """Check reference to a deliverable."""
    product = attrs.get('product')
    docset = attrs.get('docset')
    dc = attrs.get('dc')

    # Build the XPath
    base_xpath = (  # Use // to be more robust against nesting
        f'//product[@productid = {product!r}]/docset[@setid = {docset!r}]'
        f"/builddocs/language[@default = 'true' or @default = 1]"
        f"/deliverable[dc = '{dc}']"
    )
    xpath_has_sub = f'{base_xpath}[subdeliverable]'
    xpath_hasnot_sub = f'{base_xpath}[not(subdeliverable)]'
    tree = ref.getroottree()

    origin = ref.xpath(
        'concat(ancestor::product/@productid, "/",  ancestor::docset/@setid)'
    )
    # A reference to a deliverable is only valid if it exists and
    # has no subdeliverables.
    if tree.xpath(xpath_hasnot_sub):
        return None  # Valid reference found

    # If we are here, it's an invalid reference. We need to find out why.
    if tree.xpath(xpath_has_sub):
        return (
            f'Failed reference from {origin!r} to {product}/{docset}:{dc}: '
            'Referenced deliverable has subdeliverables, '
            'you must choose a subdeliverable in your reference.'
        )
    else:
        return (
            f'Failed reference from {origin!r} to {product}/{docset}:{dc}: '
            'Referenced deliverable does not exist.'
        )


def check_ref_to_link(ref: etree._Element, attrs: dict[str, str]) -> str | None:
    """Check ref to an external link."""
    product = attrs.get('product')
    docset = attrs.get('docset')
    link = attrs.get('link')

    xpath = (  # Use // to be more robust against nesting
        f'//product[@productid = {product!r}]/docset[@setid = {docset!r}]'
        f"/builddocs/language[@default = 'true' or @default = 1]"
        f"/external/link[@linkid = '{link}']"
    )

    tree = ref.getroottree()
    if not tree.xpath(xpath):
        origin = ref.xpath(
            'concat(ancestor::product/@productid, "/",  ancestor::docset/@setid)'
        )
        return (
            f'Failed reference from {origin!r} to {product}/{docset}@{link}: '
            'Referenced external link does not exist.'
        )


def check_ref_to_docset(ref: etree._Element, attrs: dict[str, str]) -> str | None:
    """Check reference to a docset."""
    product = attrs.get('product')
    docset = attrs.get('docset')
    xpath = (  # Use // to be more robust against nesting
        f'//product[@productid = {product!r}]/docset[@setid = {docset!r}]'
    )

    tree = ref.getroottree()
    if not tree.xpath(xpath):
        origin = ref.xpath(
            'concat(ancestor::product/@productid, "/",  ancestor::docset/@setid)'
        )
        return (
            f'Failed reference from {origin!r} to {product}/{docset}: '
            'Referenced docset does not exist.'
        )


def check_ref_to_product(ref: etree._Element, attrs: dict[str, str]) -> str | None:
    """Check reference to a product."""
    product = attrs.get('product')

    xpath = f'//product[@productid = {product!r}]'  # Use // to be more robust
    tree = ref.getroottree()
    if not tree.xpath(xpath):
        origin = ref.xpath(
            'concat(ancestor::product/@productid, "/",  ancestor::docset/@setid)'
        )
        return (
            f'Failed reference from {origin!r} to {product}: '
            'Referenced product does not exist.'
        )


def check_stitched_references(tree: etree._ElementTree) -> list[str]:
    """Check <ref> elements for broken references.

    This function is a Python equivalent of the
    ``global-check-ref-list.xsl`` stylesheet.

    :param tree: The tree of the stitched XML file.
    :returns: A list of error messages for any broken references found.
    """
    errors: list[str] = []

    # TODO: Make it concurrent using Python's `concurrent.futures` module.
    #       Consider using ThreadPoolExecutor or ProcessPoolExecutor to parallelize
    #       the processing of <ref> elements. Ensure thread safety when appending
    #       to the `errors` list, and handle exceptions raised during concurrent
    #       execution to avoid losing error messages.
    for ref in tree.iter('ref'):
        attrs = ref.attrib
        product = attrs.get('product')
        docset = attrs.get('docset')
        dc = attrs.get('dc')
        subdeliverable = attrs.get('subdeliverable')
        link = attrs.get('link')

        result = None
        # Case 1: Reference to a subdeliverable
        if subdeliverable and dc and docset and product:
            result = check_ref_to_subdeliverable(ref, attrs)

        # Case 2: Reference to a deliverable
        elif dc and docset and product:
            result = check_ref_to_deliverable(ref, attrs)

        # Case 3: Reference to an external link
        elif link and docset and product:
            result = check_ref_to_link(ref, attrs)

        # Case 4: Reference to a docset
        elif docset and product:
            result = check_ref_to_docset(ref, attrs)

        # Case 5: Reference to a product
        elif product:
            result = check_ref_to_product(ref, attrs)

        # Case 6: Invalid <ref> element
        else:
            origin = ref.xpath(
                'concat(ancestor::product/@productid, "/",  ancestor::docset/@setid)'
            )
            result = (
                f'Reference failed in {origin!r}. '
                'This issue should have been caught by the RNC validation: '
                'This is a docserv-stitch bug.'
            )

        if result:
            errors.append(result)

    return errors
