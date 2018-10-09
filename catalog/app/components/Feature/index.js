/* Main landing page feature */
import * as colors from 'material-ui/styles/colors';
import PropTypes from 'prop-types';
import React from 'react';
import styled from 'styled-components';

import ImageRow from 'components/ImageRow';

import background from './background.jpg';
import strings from './messages';

/* eslint-disable jsx-a11y/no-static-element-interactions */
const Feature = ({ header, tagline }) => (
  <ImageRow backgroundColor="white" src={background}>
    <Content>
      <h1 className="main">{header}</h1>
      <h2 className="main">{tagline}</h2>
    </Content>
  </ImageRow>
);

/* TODO do not abuse string tables like this; belongs in a FormattedMessage, but
 * those don't support default values well? */
Feature.defaultProps = {
  header: strings.header.defaultMessage,
};

Feature.propTypes = {
  header: PropTypes.string,
};

const Content = styled.div`
  border-bottom: 1px solid backgroundColor;
  padding: 64px;
  position: relative;
  text-align: center;

  h1.main, h2.main {
    color: ${colors.grey800};
    font-size: 4em;
    margin: 0;
    text-align: left;
    text-shadow: 0px 0px 0px black;

  }

  h1.main {
    font-weight: bold;
    margin-top: 0;
  }

  h2.main {
    margin-bottom: 64px;
  }

  .left {
    text-align: left;
  }

  .right {
    margin-top: 64px;
    text-align: right;
  }

`;

Feature.propTypes = {
  header: PropTypes.string,
  tagline: PropTypes.string,
};

/* TODO do not abuse string tables like this; belongs in a FormattedMessage, but
 * those don't support default values well? */
Feature.defaultProps = {
  header: strings.header.defaultMessage,
  tagline: strings.tagline.defaultMessage,
};

export default Feature;
