/*****************************************************************************
 * FILE:    Main
 * DATE:    2/2/2016
 * AUTHOR:  Shawn Crawley
 * COPYRIGHT: (c) 2015 Brigham Young University
 * LICENSE: BSD 2-Clause
 * CONTRIBUTIONS:   http://ignitersworld.com/lab/contextMenu.html
 *                  http://openlayers.org/
 *                  https://www.npmjs.com/package/reproject
 *
 *****************************************************************************/

/*****************************************************************************
 *                      LIBRARY WRAPPER
 *****************************************************************************/

// Global directives for JSLint/JSHint
/*global document, $, console, FormData, ol, window, setTimeout, reproject, proj4, pageX, pageY */

var HS_GIS = (function packageHydroShareGIS() {

    "use strict"; // And enable strict mode for this library

    /******************************************************
     ****************GLOBAL VARIABLES**********************
     ******************************************************/
    var currentLayers = [],
        emptyBar,
        layers,
        layersContextMenu,
        map,
        progressBar,
        progressText,
        updateProgressBar,
    // Functions
        addDefaultBeforeSendToAjax,
        addInitialEventHandlers,
        areValidFiles,
        changeBaseMap,
        checkCsrfSafe,
        editLayerName,
        getCookie,
        getUploadProgress,
        initializeLayersContextMenu,
        initializeMap,
        prepareFilesForAjax,
    //jQuery Selectors
        $currentLayersList = $('#current-layers-list');

    /******************************************************
     **************FUNCTION DECLARATIONS*******************
     ******************************************************/

    addDefaultBeforeSendToAjax = function () {
        // Add CSRF token to appropriate ajax requests
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                if (!checkCsrfSafe(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", getCookie("csrftoken"));
                }
            }
        });
    };

    addInitialEventHandlers = function () {
        $('.basemap-option').on('click', changeBaseMap);

        $('.import-btn').on('click', function () {
            var modalTitle = $(this).text();
            $('.modal-title').text(modalTitle);
            if (modalTitle.indexOf('computer') !== -1) {
                $('#btn-upload-file')
                    .text('Upload')
                    .removeAttr('disabled');
                $('.modal-body')
                    .html('<input id="input-files" type="file" multiple accept=".shp, .dbf, .shx, .prj">' +
                        '<br>' +
                        '<div id="empty-bar" class="hidden">.</div>' +
                        '<div id="progress-bar" class="hidden">.</div>' +
                        '<div id="progress-text" class="hidden">0%</div>'
                        );
                emptyBar = $('#empty-bar');
                progressBar = $('#progress-bar');
                progressText = $('#progress-text');
            } else {
                $('.modal-body').html('');
            }
            $('#uploadModal').modal('show');
        });
    };

    areValidFiles = function (files) {
        var file,
            hasShp = false,
            hasShx = false,
            hasPrj = false,
            hasDbf = false;

        for (file in files) {
            if (files.hasOwnProperty(file)) {
                if (files[file].name.endsWith('.shp')) {
                    hasShp = true;
                } else if (files[file].name.endsWith('.shx')) {
                    hasShx = true;
                } else if (files[file].name.endsWith('.prj')) {
                    hasPrj = true;
                } else if (files[file].name.endsWith('.dbf')) {
                    hasDbf = true;
                }
            }

        }
        return (hasShp && hasShx && hasPrj && hasDbf);
    };

    changeBaseMap = function () {
        $('.current-basemap-label').text('');
        $('.basemap-option').removeClass('selected-basemap-option');
        $(this).addClass('selected-basemap-option');
        $($(this).children()[0]).text(' (Current)');

        var style = $(this).attr('value'),
            i,
            ii = layers.length;

        for (i = 0; i < ii; ++i) {
            layers[i].set('visible', (layers[i].get('style') === style));
        }
    };

    // Find if method is CSRF safe
    checkCsrfSafe = function (method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    };

    editLayerName = function (e, $layerNameInput, $layerNameSpan, layerIndex) {
        if (e.which === 13) {  // Enter key
            $layerNameSpan.text($layerNameInput.val());
            $layerNameInput
                .addClass('hidden')
                .off('keyup');
            $layerNameSpan.removeClass('hidden');
            map.getLayers().item(layerIndex).set('name', $layerNameInput.val());
        } else if (e.which === 27) {  // Esc key
            $layerNameInput
                .addClass('hidden')
                .off('keyup')
                .val($layerNameSpan.text());
            $layerNameSpan.removeClass('hidden');
        }
    };

    getCookie = function (name) {
        var cookie,
            cookies,
            cookieValue = null,
            i;

        if (document.cookie && document.cookie !== '') {
            cookies = document.cookie.split(';');
            for (i = 0; i < cookies.length; i++) {
                cookie = $.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    };

    getUploadProgress = function () {
        $.ajax({
            url: 'get-upload-progress',
            type: 'GET',
            dataType: 'json',
            success: function (data) {
                if (data.hasOwnProperty('success')) {
                    var progress = Math.round(data.progress);
                    if (progress !== 100) {
                        updateProgressBar(parseInt(progress, 10) + '%');
                        setTimeout(getUploadProgress, 1000);
                    }
                }
            },
            error: function () {
                console.error("Error while retrieving progress");
            }
        });
    };

    initializeLayersContextMenu = function () {
        layersContextMenu = [
            {
                name: 'Rename',
                title: 'Rename',
                fun: function (e) {
                    var clickedElement = e.trigger.context,
                        layerIndex = Number($currentLayersList.find('li').index(clickedElement)) + 3,
                        $LayerNameSpan = $(clickedElement).find('span');

                    $LayerNameSpan.addClass('hidden');
                    $(clickedElement).find('input')
                        .removeClass('hidden')
                        .select()
                        .on('keyup', function (e) {
                            editLayerName(e, $(this), $LayerNameSpan, layerIndex);
                        });
                }
            }, {
                name: 'Zoom to',
                title: 'Zoom to',
                fun: function (e) {
                    var clickedElement = e.trigger.context,
                        ceIndex = Number($currentLayersList.find('li').index(clickedElement)),
                        layerExtent = map.getLayers().item(ceIndex + 3).getSource().getExtent(); // Ignore 3 base maps
                    map.getView().fit(layerExtent, map.getSize());
                }
            }, {
                name: 'Delete',
                title: 'Delete',
                fun: function (e) {
                    var clickedElement = e.trigger.context,
                        ceIndex = Number($currentLayersList.find('li').index(clickedElement));

                    map.getLayers().removeAt(ceIndex + 3);  // Ignore 3 base maps
                    $currentLayersList.find('li:nth-child(' + (ceIndex + 1) + ')').remove();
                }
            }
        ];
    };

    initializeMap = function () {
        // Base Layer options
        layers = [
            new ol.layer.Tile({
                style: 'Road',
                visible: false,
                source: new ol.source.MapQuest({layer: 'osm'})
            }),
            new ol.layer.Tile({
                style: 'Aerial',
                visible: false,
                source: new ol.source.MapQuest({layer: 'sat'})
            }),
            new ol.layer.Group({
                style: 'AerialWithLabels',
                visible: false,
                layers: [
                    new ol.layer.Tile({
                        source: new ol.source.MapQuest({layer: 'sat'})
                    }),
                    new ol.layer.Tile({
                        source: new ol.source.MapQuest({layer: 'hyb'})
                    })
                ]
            })
        ];

        map = new ol.Map({
            layers: layers,
            target: 'map',
            view: new ol.View({
                center: [0, 0],
                zoom: 2
            })
        });
    };

    prepareFilesForAjax = function (files) {
        var file,
            data = new FormData();

        for (file in files) {
            if (files.hasOwnProperty(file)) {
                data.append('shapefiles', files[file]);
            }
        }
        return data;
    };

    updateProgressBar = function (value) {
        progressBar.css('width', value);
        progressText.text(value);
    };

    /*
     **************ONLOAD FUNCTION*******************
     */

    $(function () {
        addDefaultBeforeSendToAjax();
        initializeMap();
        initializeLayersContextMenu();
        addInitialEventHandlers();
    });

    $(document).on('click', '#btn-upload-file', function () {
        var fileInputNode = $('#input-files')[0],
            files = fileInputNode.files,
            data;

        if (!areValidFiles(files)) {
            console.error("Invalid files. Please include four total files: .shp, .shx, .prj, and .dbf.");
        } else {
            $('#btn-upload-file').text('...')
                .attr('disabled', 'true');
            data = prepareFilesForAjax(files);

            $.ajax({
                url: 'upload-file/',
                type: 'POST',
                data: data,
                dataType: 'json',
                processData: false,
                contentType: false,
                error: function () {
                    progressBar.addClass('hidden');
                    console.error("Error!");
                },
                success: function (response) {
                    var geojsonObject,
                        newLayer,
                        projection,
                        reprojectedGeoJson,
                        fileName,
                        $lastLayerListElement;

                    updateProgressBar('100%');
                    $('#btn-upload-file').text('Done');

                    if (response.hasOwnProperty('success')) {
                        fileName = response.filename;
                        projection = response.projection;
                        proj4.defs('new_projection', projection);
                        geojsonObject = JSON.parse(response.geojson);
                        if (projection) {
                            reprojectedGeoJson = reproject(geojsonObject, proj4('new_projection'), proj4('EPSG:3857'));
                            newLayer = new ol.layer.Vector({
                                name: fileName,
                                source: new ol.source.Vector({
                                    features: (new ol.format.GeoJSON()).readFeatures(reprojectedGeoJson)
                                })
                            });
                            map.addLayer(newLayer);
                            currentLayers.push(newLayer);
                            $currentLayersList.append(
                                '<li><span class="layer-name">' + fileName + '</span><input type="text" class="edit-layer-name hidden" value="' + fileName + '"></li>'
                            );
                            $lastLayerListElement = $('#current-layers-list').find(':last-child');
                            // Apply the dropdown-on-right-click menu to new layer in list
                            $lastLayerListElement.contextMenu('menu', layersContextMenu, {
                                triggerOn: 'click',
                                displayAround: 'cursor',
                                mouseClick: 'right'
                            });
                            $lastLayerListElement.find('.layer-name').on('dblclick', function () {
                                var $layerNameSpan = $(this),
                                    layerIndex = Number($currentLayersList.find('li').index($lastLayerListElement)) + 3;

                                $layerNameSpan.addClass('hidden');
                                $lastLayerListElement.find('input')
                                    .removeClass('hidden')
                                    .select()
                                    .on('keyup', function (e) {
                                        editLayerName(e, $(this), $layerNameSpan, layerIndex);
                                    });
                            });
                        } else {
                            console.error('There is insufficient projection information to plot the shapefile.');
                        }
                    }
                }
            });

            emptyBar.removeClass('hidden');
            progressBar.removeClass('hidden');
            progressText.removeClass('hidden');
            getUploadProgress();
        }
    });
}());
