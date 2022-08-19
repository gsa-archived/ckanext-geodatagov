import logging
import xml.etree.ElementTree as ET
from builtins import object

import six
from ckan.tests import factories
from ckan.tests.helpers import reset_db
from click.testing import CliRunner, Result

import ckanext.geodatagov.cli as cli
from ckanext.geodatagov.commands import GeoGovCommand

log = logging.getLogger(__name__)

# TODO - test for output, test checking complete s3 cycle


class TestSitemapExport(object):
    @classmethod
    def setup(cls):
        reset_db()

    def create_datasets(self):

        organization = factories.Organization()
        self.dataset1 = factories.Dataset(owner_org=organization["id"])
        self.dataset2 = factories.Dataset(owner_org=organization["id"])
        self.dataset3 = factories.Dataset(owner_org=organization["id"])
        self.dataset4 = factories.Dataset(owner_org=organization["id"])

    @staticmethod
    def _handle_cli_output(cli_result: Result) -> list:
        """Parses cli output Result to an interable file_list"""

        # check successful cli run
        assert cli_result.exit_code == 0

        # the example output I have only has one element in it,
        # this will need to be updated for examples with more elements
        # checks only one list element
        assert cli_result.output.count("[") == 1
        assert cli_result.output.count("]") == 1

        file_list = [
            eval(
                cli_result.output[
                    cli_result.output.index("[") + 1 : cli_result.output.index("]") - 1
                ].strip()
            )
        ]

        return file_list

    def test_create_sitemap(self):
        """run sitemap-to-s3 and analyze results"""

        # TODO REMOVE
        import ipdb

        ipdb.set_trace()

        self.create_datasets()

        runner = CliRunner()
        raw_cli_output = runner.invoke(
            cli.sitemap_to_s3,
            args=[
                "--upload_to_s3",
                "False",
                "--page_size",
                "100",
                "--max_per_page",
                "100",
            ],
        )
        file_list = self._handle_cli_output(raw_cli_output)

        files = 0
        datasets = 0
        for site_file in file_list:
            files += 1
            """ expected something like
                <?xml version="1.0" encoding="UTF-8"?>
                <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                    <url>
                        <loc>http://ckan:5000/dataset/test_dataset_01</loc>
                        <lastmod>2020-09-29</lastmod>
                    </url>
                    <url>
                        <loc>http://ckan:5000/dataset/test_dataset_02</loc>
                        <lastmod>2020-09-29</lastmod>
                    </url>
                    ...
                </urlset>
            """
            log.info("Opening file {}".format(site_file["path"]))
            tree = ET.parse(site_file["path"])
            root = tree.getroot()
            log.info("XML Root {}".format(root))
            assert root.tag == "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset"

            prev_last_mod = ""

            dataset1_found = False
            dataset2_found = False
            dataset3_found = False
            dataset4_found = False

            for url in root:
                for child in url:
                    if child.tag == "{http://www.sitemaps.org/schemas/sitemap/0.9}loc":
                        dataset_url = child.text
                        dataset_name = dataset_url.split("/")[-1]
                        if dataset_name == self.dataset1["name"]:
                            dataset1_found = True
                        elif dataset_name == self.dataset2["name"]:
                            dataset2_found = True
                        elif dataset_name == self.dataset3["name"]:
                            dataset3_found = True
                        elif dataset_name == self.dataset4["name"]:
                            dataset4_found = True
                        datasets += 1
                    elif (
                        child.tag
                        == "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod"
                    ):
                        last_mod = child.text
                        log.info("{} >= {} ".format(prev_last_mod, last_mod))
                        assert last_mod >= prev_last_mod
                        prev_last_mod = last_mod
                    else:
                        raise Exception("Unexpected tag")

        assert files == 1
        assert datasets >= 4  # at least this four
        assert dataset1_found
        assert dataset2_found
        assert dataset3_found
        assert dataset4_found
