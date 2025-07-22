# syntax=docker/dockerfile:1.7

###############################################################################
# 1. Build stage: Install daps and suse-xsl-stylesheets
###############################################################################
ARG OPENSUSE_VERSION=15.6
ARG URL=https://download.opensuse.org/repositories

FROM opensuse/leap:${OPENSUSE_VERSION} AS build


# Add the Documentation:Tools OBS repository and refresh
RUN zypper ar -f ${URL}/Documentation:/Tools/'$releasever' Documentation_Tools ; \
    zypper --gpg-auto-import-keys --non-interactive refresh

# Now install all required packages (from default + custom repo)
RUN zypper --non-interactive install --no-recommends \
        curl ca-certificates sgml-skel gzip optipng \
        google-noto-sans-jp-regular-fonts google-noto-sans-jp-bold-fonts \
        google-noto-sans-sc-regular-fonts google-noto-sans-sc-bold-fonts \
        google-noto-sans-kr-regular-fonts google-noto-sans-kr-bold-fonts \
        google-noto-sans-tc-regular-fonts google-noto-sans-tc-bold-fonts \
        arabic-amiri-fonts sil-charis-fonts gnu-free-fonts \
        google-opensans-fonts dejavu-fonts google-poppins-fonts suse-fonts \
        daps suse-xsl-stylesheets rsvg-convert geekodoc tar w3m jq openssh-clients && \
    zypper clean --all

# Remove unneeded files and packages to minimize image size
RUN rm -rf \
      /usr/bin/inkview \
      /usr/share/icons \
      /usr/share/man \
      /usr/share/help \
      /usr/share/locale \
      /usr/share/doc \
      /usr/share/libreoffice/help \
      /usr/share/inkscape/tutorials \
      /usr/share/inkscape/examples \
      /usr/share/dia/help \
      /usr/share/ghostscript/*/doc \
      /usr/lib64/libreoffice/help \
      /usr/lib64/libreoffice/program/wizards \
      /usr/lib64/libreoffice/share/gallery \
      /usr/lib64/libreoffice/share/template \
      /usr/lib64/ruby/*/rdoc \
      /usr/share/ghostscript/*/examples \
      /usr/share/inkscape/icons \
      /usr/share/kbd/keymaps/legacy \
      /usr/share/xml/docbook/schema/xsd \
      /usr/share/xml/docbook/stylesheet/nwalsh*/*/slides \
      /var/log/* \
      /usr/local/man \
      /usr/lib64/libreoffice/share/config \
    || true

RUN rpm --erase --nodeps adwaita-icon-theme \
      desktop-file-utils gtk2-tools gtk3-tools \
      hicolor-icon-theme libreoffice-branding-openSUSE \
      libreoffice-icon-themes || true


###############################################################################
# 2. Runtime stage: Minimal image with only daps and its dependencies
###############################################################################
FROM opensuse/leap:${OPENSUSE_VERSION}

ARG DAPS_VERSION=4.0beta10
ARG GEEKODOC_VERSION=2.3.1.1
ARG SUSE_XSL_VERSION=2.95.12

LABEL org.opencontainers.image.vendor="openSUSE"
LABEL org.opencontainers.image.title="DAPS CI Image"
LABEL org.opencontainers.image.description="Minimal openSUSE Leap-based image for DAPS and documentation building (used in CI/CD)."
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.url="https://github.com/openSUSE/docbuild"
LABEL org.opencontainers.image.source="https://github.com/openSUSE/docbuild"
LABEL org.opencontainers.image.licenses="GPL-2.0-or-later"
LABEL org.opencontainers.image.authors="Tom Schraitle <tomschr@noreply.github.com>"
# Custom component labels
LABEL com.opensuse.docbuild.daps.version="${DAPS_VERSION}"
LABEL com.opensuse.docbuild.suse-xsl-stylesheets="${SUSE_XSL_VERSION}"
LABEL com.opensuse.docbuild.geekodoc.version="${GEEKODOC_VERSION}"


# Copy daps and suse-xsl-stylesheets from build stage
COPY --from=build /usr /usr
COPY --from=build /etc /etc

# Final cleanup to reduce image size
RUN rm -rf /var/cache/zypp/* /var/log/* /tmp/* /usr/share/man /usr/share/doc /usr/share/locale

# Set non-root user (optional, recommended for security)
RUN useradd --create-home --shell /bin/bash dapsuser
USER dapsuser

RUN mkdir --parents ~/.config/daps && \
    echo 'DOCBOOK5_RNG_URI="urn:x-suse:rng:v2:geekodoc-flat"' > ~/.config/daps/dapsrc

WORKDIR /workspace

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV TERM xterm-256color

# ENTRYPOINT ["daps"]
# CMD ["--help"]
