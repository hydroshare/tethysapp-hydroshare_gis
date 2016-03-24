var SLD_TEMPLATES = (function () {
    "use strict";

    var point,
        polygon,
        polyline,
        line,
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

    labels =
        '<TextSymbolizer>' +
        '<Label>' +
        '<PropertyName>{{label-field}}</PropertyName>' +
        '</Label>' +
        '<Font>' +
        //'<CssParameter name="font-family">Arial</CssParameter>' +
        '<CssParameter name="font-size">{{font-size}}</CssParameter>' +
        //'<CssParameter name="font-style">normal</CssParameter>' +
        //'<CssParameter name="font-weight">normal</CssParameter>' +
        '</Font>' +
        //'<LabelPlacement>' +
        //'<PointPlacement>' +
        //'<AnchorPoint>' +
        //'<AnchorPointX>0.5</AnchorPointX>' +
        //'<AnchorPointY>1.0</AnchorPointY>' +
        //'</AnchorPoint>' +
        //'<Displacement>' +
        //'<DisplacementX>0</DisplacementX>' +
        //'<DisplacementY>-12</DisplacementY>' +
        //'</Displacement>' +
        //'</PointPlacement>' +
        //'</LabelPlacement>' +
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
        var style,
            sldString = rawSldString;

        for (style in cssStyles) {
            if (cssStyles.hasOwnProperty(style)) {
                sldString = sldString.replace('{{' + style + '}}', cssStyles[style]);
            }
        }
        return sldString;
    };

    geomTypeDict = {
        'point': point,
        'polygon': polygon,
        'line': polyline
    };

    return {
        getSldString: function (cssStyles, geomType, layerId) {
            var rawSldString;

            cssStyles = {
                'layer-id': layerId
            };

            if (cssStyles.labels) {
                rawSldString = addLabels(geomTypeDict[geomType]);
            } else {
                rawSldString = geomTypeDict[geomType];
            }
            return populateValues(rawSldString, cssStyles);
        }
    };
}());