.. _build-deliverables:

Building Deliverables
=====================

The :command:`docbuild build run` subcommand is used to build deliverables from source files. It processes the source files and generates the output in the specified format, such as HTML or PDF.

.. code-block:: bash
   :caption: Synopsis of :command:`docbuild build run`

   docbuild build run [OPTIONS] DOCTYPE [DOCTYPE ...]

The syntax is modeled in the :class:`~docbuild.models.doctype.Doctype` class.


Build failure email
-------------------

Set the following in your environment TOML to notify product maintainers on a failed
:command:`docbuild build run`.
Each product's :code:`<maintainers><contact>` addresses receive one message for that
product. Administrators receive one digest including failures without a product.

.. code-block:: toml

   [general]
   enable_mail = true

   [mail]
   admin_emails = ["docs-admin@example.org"]
   sender = "docbuild@example.org"
   smtp_host = "smtp.example.org"
   smtp_port = 587
   tls = "starttls"
   timeout = 10

Use :code:`implicit` for TLS on connection (usually port 465), or :code:`none`
for a trusted local relay. The timeout is in seconds.
For authenticated delivery, supply both :envvar:`DOCBUILD_SMTP_USERNAME` and
:envvar:`DOCBUILD_SMTP_PASSWORD` in the process environment and use TLS.
Omit both variables for an unauthenticated relay.
