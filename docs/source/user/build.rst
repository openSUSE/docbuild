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

TLS is required for all notification mail.
STARTTLS (:code:`starttls`) commonly uses port 587.
For implicit TLS, set :code:`tls = "implicit"` and configure the relay port, commonly 465.
The timeout is in seconds.
For authenticated delivery, supply both :envvar:`DOCBUILD_SMTP_USERNAME` and
:envvar:`DOCBUILD_SMTP_PASSWORD` in the process environment.
Omit both variables for an unauthenticated relay.
