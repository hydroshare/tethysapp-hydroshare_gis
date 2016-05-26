var SLD_TEMPLATES = (function () {
    "use strict";

    var point,
        polygon,
        polyline,
        line,
        raster,
        labels,
        addLabels,
        header,
        footer,
        fill,
        stroke,
        populateValues,
        geomTypeDict;

    header =
        '<StyledLayerDescriptor version="1.0.0">' +
        '<NamedLayer>' +
        '<Name>{{layer-id}}</Name>' +
        '<UserStyle>' +
        '<FeatureTypeStyle>' +
        '<Rule>';

    footer =
        '</Rule>' +
        '</FeatureTypeStyle>' +
        '</UserStyle>' +
        '</NamedLayer>' +
        '</StyledLayerDescriptor>';

    fill =
        '<Fill>' +
        '<CssParameter name="fill">{{fill}}</CssParameter>' +
        '<CssParameter name="fill-opacity">{{fill-opacity}}</CssParameter>' +
        '</Fill>';

    stroke =
        '<Stroke>' +
        '<CssParameter name="stroke">{{stroke}}</CssParameter>' +
        '<CssParameter name="stroke-width">{{stroke-width}}</CssParameter>' +
        '<CssParameter name="stroke-opacity">{{stroke-opacity}}</CssParameter>' +
        '</Stroke>';

    line = '<LineSymbolizer>' + stroke + '</LineSymbolizer>';

    point =
        header +
        '<PointSymbolizer>' +
        '<Graphic>' +
        '<Mark>' +
        '<WellKnownName>{{point-shape}}</WellKnownName>' +
        fill +
        stroke +
        '</Mark>' +
        '<Size>{{point-size}}</Size>' +
        '</Graphic>' +
        '</PointSymbolizer>' +
        footer;

    polygon =
        header +
        '<PolygonSymbolizer>' +
        fill +
        '</PolygonSymbolizer>' +
        line +
        footer;

    polyline = header + line + footer;

    raster =
        header +
        '<RasterSymbolizer>' +
        '<ColorMap>' +
        '{{color-map}}' +
        '</ColorMap>' +
        '</RasterSymbolizer>' +
        footer;

    labels =
        '<TextSymbolizer>' +
        '<Label>' +
        '<PropertyName>{{label-field}}</PropertyName>' +
        '</Label>' +
        '<Font>' +
        '<CssParameter name="font-size">{{font-size}}</CssParameter>' +
        '</Font>' +
        '<Fill>' +
        '<CssParameter name="fill">{{font-fill}}</CssParameter>' +
        '<CssParameter name="fill-opacity">{{font-fill-opacity}}</CssParameter>' +
        '</Fill>' +
        '</TextSymbolizer>';

    addLabels = function (geometry) {
        var insertionIndex = geometry.indexOf('</Rule>');
        return geometry.slice(0, insertionIndex) + labels + geometry.slice(insertionIndex);
    };

    populateValues = function (rawSldString, cssStyles) {
        var colorMap,
            colorMapXml = '',
            sldString = rawSldString;

        Object.keys(cssStyles).forEach(function (style) {
            if (style === 'color-map') {
                colorMap = JSON.parse(JSON.stringify(cssStyles[style]));
                // TEMPFIX: Hide edge artifacts
                // See http://osgeo-org.1560.x6.nabble.com/Artifacts-in-reprojected-rasters-has-this-been-fixed-td5213036.html
                colorMap[255] = {
                    color: '#000000',
                    opacity: 0
                };
                // END TEMPFIX
                Object.keys(colorMap).sort(function (a, b) {return Number(a) - Number(b); }).forEach(function (quantity) {
                    colorMapXml += '<ColorMapEntry color="' + colorMap[quantity].color + '" quantity="' + quantity + '" opacity="' + colorMap[quantity]['opacity'] + '"/>';
                });
                sldString = sldString.replace('{{' + style + '}}', colorMapXml);
            }
            sldString = sldString.replace('{{' + style + '}}', cssStyles[style]);
        });
        return sldString;
    };

    geomTypeDict = {
        'point': point,
        'polygon': polygon,
        'line': polyline,
        'None': raster
    };

    return {
        getSldString: function (cssStyles, geomType, layerId) {
            var rawSldString;

            cssStyles['layer-id'] = layerId;

            if (cssStyles.labels) {
                rawSldString = addLabels(geomTypeDict[geomType]);
            } else {
                rawSldString = geomTypeDict[geomType];
            }
            return populateValues(rawSldString, cssStyles);
        }
    };
}());