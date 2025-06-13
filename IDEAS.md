# Ideas

This is a unsorted collection of ideas what could be implemented.

* Doctypes and language.
  The language type allows en-us, de-de, and the asterisk to match
  "all" languages. However, we don't have an expressive value that
  matches "all languages except English".
  Maybe allow "-" in front of the language?
  * "-en-us" would match all languages minus English.
  * "-en-us,-de-de" would match all languages minus English and German.
    Should the second dash be optional?

* `Deliverable`
   support subdeliverables?

* Implement a "check environment" function.
  Before we really do anything, this check some prerequisites:
   * Checks if certain commands are available (e.g. `git`, `jing`)
   * Check if commands have a minimum version
   * Check if the available space is enough (can be customized in the envconfig)
   * More...?
  
  This should help that it breaks in the middle of, for example, a build operation.
