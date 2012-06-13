# -*- coding: utf-8 -*-
"""
    test_pagination

    Test the pagination feature

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import unittest2 as unittest

from mongoengine import connect, Document, IntField
from mongoengine.connection import _get_connection
from monstor.utils.web import Pagination


class TestDocument(Document):
    sequence = IntField()


def get_seq(documents):
    """
    :param documents: A list of mongo documents

    :return: Returns the list of sequence from the list of documents
    """
    return [d.sequence for d in documents]


class TestPagination(unittest.TestCase):
    """Test the pagination features"""

    @classmethod
    def setUpClass(cls):
        connect("test_pagination")

    def setUp(self):
        for x in xrange(0, 100):
            TestDocument(sequence=x).save()

    def test_count(self):
        "Test the count attribute"
        self.assertEqual(
            Pagination(1, 10, TestDocument.objects()).count, 100
        )
        self.assertEqual(
            Pagination(1, 10, TestDocument.objects(sequence__lt=10)).count,
            10
        )

    def test_all_items(self):
        "Test the all_items method"
        self.assertEqual(
            len(Pagination(1, 10, TestDocument.objects()).all_items()), 100
        )

    def test_items(self):
        "Test the items method"
        self.assertEqual(
            set(get_seq(Pagination(1, 10, TestDocument.objects()).items())),
            set(xrange(0, 10))
        )

    def test_has_prev(self):
        "Test the has_prev method"
        self.assertFalse(Pagination(1, 10, TestDocument.objects()).has_prev)
        self.assertTrue(Pagination(2, 10, TestDocument.objects()).has_prev)

    def test_has_next(self):
        "Test the has_next attribute"
        self.assertFalse(Pagination(10, 10, TestDocument.objects()).has_next)
        self.assertTrue(Pagination(1, 10, TestDocument.objects()).has_next)

    def test_next(self):
        "Test the next attribute"
        self.assertEqual(
            get_seq(Pagination(1, 10, TestDocument.objects()).next().items()),
            get_seq(Pagination(2, 10, TestDocument.objects()).items()),
        )

    def test_prev(self):
        "Test the prev attribute"
        self.assertEqual(
            get_seq(Pagination(2, 10, TestDocument.objects()).prev().items()),
            get_seq(Pagination(1, 10, TestDocument.objects()).items()),
        )

    def test_pages(self):
        "Test the pages attribute"
        self.assertEqual(Pagination(1, 10, TestDocument.objects()).pages, 10)
        self.assertEqual(Pagination(1, 5, TestDocument.objects()).pages, 20)
        self.assertEqual(Pagination(1, 100, TestDocument.objects()).pages, 1)
        self.assertEqual(
            Pagination(1, 10, TestDocument.objects(sequence__gt=50)).pages, 5
        )

    def tearDown(self):
        TestDocument.drop_collection()

    @classmethod
    def tearDownClass(cls):
        c = _get_connection()
        c.drop_database('test_pagination')


if __name__ == '__main__':
    unittest.main()
